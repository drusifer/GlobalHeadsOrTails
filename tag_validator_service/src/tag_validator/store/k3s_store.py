"""Kubernetes / k3s Secrets Store Adapter.

Directly manages tag keys as native k3s Secret objects in the cluster.
"""

from __future__ import annotations

import logging

from ..models import TagSecret

log = logging.getLogger(__name__)

try:
    from kubernetes import client as k8s_client  # type: ignore
    from kubernetes import config as k8s_config  # type: ignore
    from kubernetes.client.rest import ApiException  # type: ignore

    K8S_AVAILABLE = True
except ImportError:
    k8s_client = None  # type: ignore
    k8s_config = None  # type: ignore
    ApiException = Exception  # type: ignore
    K8S_AVAILABLE = False


class K3sSecretStore:
    """Manages tag keys as Kubernetes Secret objects in k3s."""

    def __init__(
        self,
        namespace: str = "tag-secrets",
        kubeconfig_path: str | None = None,
    ) -> None:
        self.namespace = namespace
        self.kubeconfig_path = kubeconfig_path
        self._v1: k8s_client.CoreV1Api | None = None
        self._initialized = False

        if not K8S_AVAILABLE:
            log.warning("kubernetes python client is not installed. K3sSecretStore unavailable.")
            return

        self._init_client()

    def _init_client(self) -> None:
        if not K8S_AVAILABLE:
            return

        try:
            if self.kubeconfig_path:
                k8s_config.load_kube_config(config_file=self.kubeconfig_path)
                log.info(f"Loaded kubeconfig from {self.kubeconfig_path}")
            else:
                try:
                    k8s_config.load_incluster_config()
                    log.info("Loaded in-cluster Kubernetes config")
                except Exception:
                    k8s_config.load_kube_config()
                    log.info("Loaded default local kubeconfig")

            self._v1 = k8s_client.CoreV1Api()
            self._initialized = True
        except Exception as e:
            log.warning(f"Failed to initialize Kubernetes API client: {e}")
            self._initialized = False

    def is_healthy(self) -> bool:
        if not self._initialized or not self._v1:
            return False
        try:
            self._v1.get_api_resources()
            return True
        except Exception as e:
            log.error(f"K3s cluster health check failed: {e}")
            return False

    def get_key(self, uid: str, include_deleted: bool = False) -> TagSecret | None:
        if not self._initialized or not self._v1:
            log.error("K3s client not initialized")
            return None

        clean_uid = uid.strip().replace(":", "").replace("-", "").upper()
        secret_name = f"tag-key-{clean_uid.lower()}"

        try:
            secret = self._v1.read_namespaced_secret(
                name=secret_name,
                namespace=self.namespace,
            )
            if not secret.data:
                return None
            parsed = TagSecret.from_k8s_secret_data(secret.data)
            if not include_deleted and parsed.status == "deleted":
                return None
            return parsed
        except ApiException as e:
            if e.status == 404:
                return None
            log.error(f"Error reading secret {secret_name} from k3s: {e}")
            return None
        except Exception as e:
            log.error(f"Unexpected error reading secret {secret_name}: {e}")
            return None

    def save_key(self, secret: TagSecret) -> bool:
        from .base import KeyConflictError

        if not self._initialized or not self._v1:
            log.error("K3s client not initialized")
            return False

        secret_name = secret.secret_name
        body = k8s_client.V1Secret(
            api_version="v1",
            kind="Secret",
            type="Opaque",
            metadata=k8s_client.V1ObjectMeta(
                name=secret_name,
                namespace=self.namespace,
                labels={
                    "app.kubernetes.io/name": "tag-validator-service",
                    "app.kubernetes.io/component": "k3-secret",
                    "app.kubernetes.io/status": secret.status,
                    "tag-uid": secret.uid.lower(),
                },
            ),
            data=secret.to_k8s_secret_data(),
        )

        try:
            # Check if secret already exists
            try:
                existing = self._v1.read_namespaced_secret(name=secret_name, namespace=self.namespace)
                if existing.data:
                    parsed_existing = TagSecret.from_k8s_secret_data(existing.data)
                    # WORM check: immutable key material
                    if parsed_existing.k3 != secret.k3:
                        raise KeyConflictError(
                            f"Tag key for UID '{secret.uid}' is immutable and cannot be overwritten with a different key."
                        )
                # Key matches -> replace/update metadata
                self._v1.replace_namespaced_secret(
                    name=secret_name,
                    namespace=self.namespace,
                    body=body,
                )
                log.info(f"Updated k3s Secret metadata: {secret_name} in {self.namespace}")
            except ApiException as e:
                if e.status == 404:
                    # Does not exist -> Create
                    self._v1.create_namespaced_secret(
                        namespace=self.namespace,
                        body=body,
                    )
                    log.info(f"Created k3s Secret: {secret_name} in {self.namespace}")
                else:
                    raise
            return True
        except KeyConflictError:
            raise
        except Exception as e:
            log.error(f"Failed to save k3s Secret {secret_name}: {e}")
            return False

    def delete_key(self, uid: str) -> bool:
        """Soft-deletes a tag secret in k3s (tombstoning). Does NOT delete the secret."""
        from datetime import datetime, timezone

        if not self._initialized or not self._v1:
            return False

        clean_uid = uid.strip().replace(":", "").replace("-", "").upper()
        secret_name = f"tag-key-{clean_uid.lower()}"

        try:
            existing = self._v1.read_namespaced_secret(name=secret_name, namespace=self.namespace)
            if not existing.data:
                return False

            parsed = TagSecret.from_k8s_secret_data(existing.data)
            parsed.status = "deleted"
            parsed.deleted_at = datetime.now(timezone.utc).isoformat()

            body = k8s_client.V1Secret(
                api_version="v1",
                kind="Secret",
                type="Opaque",
                metadata=k8s_client.V1ObjectMeta(
                    name=secret_name,
                    namespace=self.namespace,
                    labels={
                        "app.kubernetes.io/name": "tag-validator-service",
                        "app.kubernetes.io/component": "k3-secret",
                        "app.kubernetes.io/status": "deleted",
                        "tag-uid": parsed.uid.lower(),
                    },
                    annotations={
                        "app.kubernetes.io/deleted-at": parsed.deleted_at,
                    },
                ),
                data=parsed.to_k8s_secret_data(),
            )
            self._v1.replace_namespaced_secret(name=secret_name, namespace=self.namespace, body=body)
            log.info(f"Soft-deleted k3s Secret (tombstone): {secret_name}")
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            log.error(f"Failed to soft-delete k3s Secret {secret_name}: {e}")
            return False
        except Exception as e:
            log.error(f"Unexpected error soft-deleting k3s Secret {secret_name}: {e}")
            return False

    def undelete_key(self, uid: str) -> bool:
        """Restores a soft-deleted tag secret back to active status in k3s."""
        if not self._initialized or not self._v1:
            return False

        clean_uid = uid.strip().replace(":", "").replace("-", "").upper()
        secret_name = f"tag-key-{clean_uid.lower()}"

        try:
            existing = self._v1.read_namespaced_secret(name=secret_name, namespace=self.namespace)
            if not existing.data:
                return False

            parsed = TagSecret.from_k8s_secret_data(existing.data)
            parsed.status = "active"
            parsed.deleted_at = None

            body = k8s_client.V1Secret(
                api_version="v1",
                kind="Secret",
                type="Opaque",
                metadata=k8s_client.V1ObjectMeta(
                    name=secret_name,
                    namespace=self.namespace,
                    labels={
                        "app.kubernetes.io/name": "tag-validator-service",
                        "app.kubernetes.io/component": "k3-secret",
                        "app.kubernetes.io/status": "active",
                        "tag-uid": parsed.uid.lower(),
                    },
                ),
                data=parsed.to_k8s_secret_data(),
            )
            self._v1.replace_namespaced_secret(name=secret_name, namespace=self.namespace, body=body)
            log.info(f"Restored k3s Secret to active: {secret_name}")
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            log.error(f"Failed to undelete k3s Secret {secret_name}: {e}")
            return False
        except Exception as e:
            log.error(f"Unexpected error undeleting k3s Secret {secret_name}: {e}")
            return False

    def list_uids(self, include_deleted: bool = False) -> list[str]:
        if not self._initialized or not self._v1:
            return []

        try:
            selector = "app.kubernetes.io/component=k3-secret"
            if not include_deleted:
                selector += ",app.kubernetes.io/status=active"

            secrets_list = self._v1.list_namespaced_secret(
                namespace=self.namespace,
                label_selector=selector,
            )
            uids = []
            for item in secrets_list.items:
                if item.metadata and item.metadata.labels and "tag-uid" in item.metadata.labels:
                    uids.append(item.metadata.labels["tag-uid"].upper())
                elif item.data and "uid" in item.data:
                    parsed = TagSecret.from_k8s_secret_data(item.data)
                    if include_deleted or parsed.status == "active":
                        uids.append(parsed.uid)
            return sorted(uids)
        except Exception as e:
            log.error(f"Failed to list k3s Secrets: {e}")
            return []
