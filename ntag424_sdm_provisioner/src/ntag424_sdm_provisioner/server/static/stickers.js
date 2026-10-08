/* Coin-owned album and exact-copy wager controls. */
window.CoinStickers = (() => {
  let coin = '', catalog = null, copies = [], challenge = null, signature = '', busy = false;
  const seenWagerEvolutions = new Set();
  const $ = id => document.getElementById(id);
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const image = (family, level) => `/static/stickers/${encodeURIComponent(family)}-${level}.webp`;
  const credentials = () => {
    const query = new URLSearchParams(location.search);
    return {uid:query.get('uid') || '', ctr:query.get('ctr') || '', cmac:query.get('cmac') || ''};
  };
  function appendAuth(form) { Object.entries(credentials()).forEach(([key,value]) => form.set(key,value)); }
  function info(copy) {
    const family = copy.family || catalog?.families.find(f => f.id === copy.family_id);
    const form = copy.form || family?.forms.find(f => f.level === copy.level);
    return {family,form};
  }
  function title(copy) {
    const {family,form} = info(copy);
    return `${family?.name || copy.family_id} — ${form?.name || copy.family_id} · ${family?.rarity || ''} · Level ${copy.level}`;
  }
  function options(name, optional) {
    const groups = new Map();
    copies.filter(s => !s.locked_challenge_id).forEach(s => {
      const key = `${s.family_id}:${s.level}`;
      if (!groups.has(key)) groups.set(key, {copy:s,count:0});
      groups.get(key).count++;
    });
    let html = optional ? `<label class="sticker-choice"><input type="radio" name="${name}" value="" checked><span>No sticker wager</span></label>` : '';
    for (const {copy,count} of groups.values()) {
      html += `<label class="sticker-choice"><input type="radio" name="${name}" value="${escape(copy.id)}" ${optional ? '' : 'required'}><img src="${image(copy.family_id,copy.level)}" alt=""><span>${escape(title(copy))}<br><small>${count} available · wager one copy</small></span></label>`;
    }
    if (!groups.size && !optional) html += '<p>No unlocked stickers available. Decline this offer or collect more.</p>';
    return html;
  }
  function renderAlbum() {
    const album = $('sticker-album');
    if (!album || !catalog) return;
    if ($('sticker-lore')) $('sticker-lore').textContent = catalog.narrative;
    const owned = new Set(copies.map(s => `${s.family_id}:${s.level}`));
    $('sticker-progress').textContent = coin ? `${coin} · ${owned.size}/36 forms collected · ${copies.length} copies` : 'Tap a coin to see its collection.';
    album.innerHTML = coin ? catalog.families.filter(family => copies.some(s => s.family_id === family.id)).map(family => `<details class="sticker-family"><summary>${escape(family.name)} · <span class="sticker-rarity ${family.rarity}">${family.rarity}</span></summary><div class="sticker-grid">${family.forms.filter(form => owned.has(`${family.id}:${form.level}`)).map(form => {
      const matching = copies.filter(s => s.family_id === family.id && s.level === form.level);
      const locked = matching.filter(s => s.locked_challenge_id).length;
      return `<article class="sticker-card"><img loading="lazy" src="${image(family.id,form.level)}" alt="${escape(form.name)}"><h4>${escape(form.name)}</h4><div class="sticker-meta"><span class="sticker-rarity ${family.rarity}">${family.rarity}</span> · Level ${form.level}<br>${matching.length} owned${locked ? ` · ${locked} locked in wager` : ''}</div><blockquote>“${escape(form.quote)}”</blockquote></article>`;
    }).join('')}</div></details>`).join('') : '';
    if (coin && !copies.length) album.innerHTML = '<p>No stickers collected yet. Flip this coin for a chance to find one.</p>';
  }
  function renderChoices() {
    const picker = $('wager-create-options');
    if (picker) {
      const selected = picker.querySelector('input:checked')?.value || '';
      picker.innerHTML = options('sticker_id',true);
      for (const input of picker.querySelectorAll('input')) input.checked = input.value === selected;
      if (!picker.querySelector('input:checked')) picker.querySelector('input').checked = true;
    }
  }
  function renderWager() {
    const panel = $('wager-active');
    if (!panel) return;
    if (!challenge?.wagered) { panel.hidden = true; return; }
    panel.hidden = false;
    const involved = [challenge.challenger_coin_name,challenge.challenged_coin_name].includes(coin);
    if (!involved) { panel.hidden = true; return; }
    const stakes = challenge.stakes || [];
    const terms = stakes.map(s => `<p>${escape(s.coin_name)} offers <strong>${escape(title(s))}</strong></p>`).join('');
    const awaiting = challenge.wager_status === 'awaiting_acceptance';
    let actions = '';
    if (awaiting && coin === challenge.challenged_coin_name) {
      actions = `<form id="wager-accept-form"><p>Choose your sticker. Review both offers before accepting.</p><div class="sticker-choices">${options('accept_sticker_id',false)}</div><p id="wager-review" class="wager-terms">Select a sticker to review the swap.</p><button type="submit" id="wager-accept-button" disabled>Accept wager and start Flip Off</button></form>`;
    } else if (awaiting) actions = '<p>Waiting for the opponent to choose a sticker and agree. Flips do not count yet.</p>';
    if (awaiting) actions += `<button type="button" id="wager-cancel">${coin === challenge.challenged_coin_name ? 'Decline offer' : 'Cancel offer'} · return sticker</button>`;
    const status = {accepted:'Both stickers are locked. Winner keeps both.',settled:'Wager settled: winner received both stickers. Any matching triples evolve automatically.',returned:'Wager ended: each sticker returned to its original coin. Any matching triples evolve automatically.'}[challenge.wager_status] || 'Winner keeps both stickers. Ties and cancellations return originals.';
    panel.innerHTML = `<h3>Sticker wager</h3>${terms}<p class="wager-terms">${status}</p>${actions}<p id="wager-action-status" role="status"></p>`;
    $('wager-cancel')?.addEventListener('click',() => act('cancel'));
    $('wager-accept-form')?.addEventListener('change',event => {
      const chosen = copies.find(s => s.id === event.target.value);
      if (!chosen) return;
      $('wager-review').textContent = `You wager ${title(chosen)}. Winner keeps both stickers; you may lose this copy.`;
      $('wager-accept-button').disabled = false;
    });
    $('wager-accept-form')?.addEventListener('submit',event => {
      event.preventDefault();
      const chosen = new FormData(event.target).get('accept_sticker_id');
      if (chosen) act('accept', chosen);
    });
  }
  async function act(action, stickerId) {
    if (busy) return;
    busy = true;
    const status = $('wager-action-status');
    try {
      const response = await fetch(`/challenge/${action}`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...credentials(),challenge_id:challenge.id,sticker_id:stickerId})});
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Wager action failed.');
      await refresh(true);
    } catch (error) { if (status) { status.textContent = error.message; status.className = 'wager-error'; } }
    finally { busy = false; }
  }
  async function refresh(force = false) {
    const response = await fetch('/api/stickers?coin_name=' + encodeURIComponent(coin));
    if (!response.ok) throw new Error('Could not load stickers.');
    const data = await response.json();
    const next = JSON.stringify([data.stickers,data.challenge]);
    if (force || next !== signature || !catalog) {
      signature = next; catalog = data.catalog; copies = coin ? data.stickers : []; challenge = data.challenge;
      const open = [...document.querySelectorAll('.sticker-family')].map(el => el.open);
      renderAlbum(); document.querySelectorAll('.sticker-family').forEach((el,i) => el.open = !!open[i]);
      renderChoices(); renderWager();
      if (challenge && !seenWagerEvolutions.has(challenge.id) && challenge.wager_evolutions?.length) {
        seenWagerEvolutions.add(challenge.id);
        const messages = challenge.wager_evolutions.filter(event => event.sticker.coin_name === coin)
          .map(event => `3 copies combined automatically after the wager: ${title(event.sticker)}!`);
        if (messages.length && $('sticker-reveal')) {
          $('sticker-reveal').hidden = false;
          $('sticker-reveal').textContent = messages.join(' ');
        }
      }
    }
    if (typeof renderBattles === 'function') renderBattles(data.active_challenges);
    if (typeof renderRecentCompleted === 'function') renderRecentCompleted(data.recent_completed);
    return data;
  }
  function onAward(award) {
    if (!award) return;
    const notices = [];
    if (award.drop) notices.push(`Sticker found: ${title(award.drop)}!`);
    for (const event of award.evolutions || []) notices.push(`3 copies combined automatically: ${title(event.sticker)}!`);
    if (notices.length && $('sticker-reveal')) {
      $('sticker-reveal').hidden = false;
      $('sticker-reveal').textContent = notices.join(' ');
    }
    refresh(true).catch(() => {});
  }
  function init(name) {
    coin = name || '';
    refresh().catch(() => { if ($('sticker-progress')) $('sticker-progress').textContent = 'Collection unavailable. Please refresh to try again.'; });
    if (coin) setInterval(() => { if (!document.hidden && !busy) refresh().catch(() => {}); },3000);
  }
  return {init,appendAuth,onAward,refresh};
})();
