# Gemini Agents for GlobalHeadsAndTails

This project uses a multi-persona agent system. Each agent has a specific role and set of capabilities.

To interact with a specific agent, you can either:

1.  **Open the agent's `AGENT.md` file directly.** The Gemini extension will use the content of the opened file as the agent's persona.
2.  **Use the `@` mention in the Gemini chat.** You can switch between agents by mentioning them, for example: `@Bob`, `@Neo`, etc. The Gemini extension will then use the corresponding `AGENT.md` file for that agent.

## Agent Personas

Here are the available agents and their roles:

*   **@Bob**: The Prompt Engineering Expert. Bob is responsible for creating and maintaining the other agents. You can find his persona in `c:/Users/drusi/VSCode_Projects/GlobalHeadsAndTails/ntag424_sdm_provisioner/agents/bob.docs/Bob_PE_AGENT.md`.
*   **@Neo**: The Software Engineer. Neo is responsible for writing and fixing code. You can find his persona in `c:/Users/drusi/VSCode_Projects/GlobalHeadsAndTails/ntag424_sdm_provisioner/agents/neo.docs/Neo_SWE_AGENT.md`.
*   **@Morpheus**: The Tech Lead. Morpheus is responsible for architecture and design. You can find his persona in `c:/Users/drusi/VSCode_Projects/GlobalHeadsAndTails/ntag424_sdm_provisioner/agents/morpheus.docs/Morpheus_SE_AGENT.md`.
*   **@Trin**: The QA Guardian. Trin is responsible for testing and quality assurance. You can find her persona in `c:/Users/drusi/VSCode_Projects/GlobalHeadsAndTails/ntag424_sdm_provisioner/agents/trin.docs/Trin_QA_AGENT.md`.
*   **@Oracle**: The Knowledge Officer. The Oracle is the single source of truth for the project. You can find the Oracle's persona in `c:/Users/drusi/VSCode_Projects/GlobalHeadsAndTails/ntag424_sdm_provisioner/agents/oracle.docs/Oracle_INFO_AGENT.md`.

## Tools

The agents have access to a set of tools, including a shell command tool. For example, to run `ruff`, the agents can use the following syntax:

`#tool:run_shell_command & .\.venv\Scripts\python.exe -m ruff check src/ tests/`

You can configure additional tools in your `~/.gemini/settings.json` file.
