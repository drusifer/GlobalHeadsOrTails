/* Coin-owned album and exact-copy wager controls. */
window.CoinStickers = (() => {
  let coin = '', catalog = null, copies = [], challenge = null, signature = '', busy = false;
  let selectedPack = '', search = '';
  const seenWagerEvolutions = new Set();
  const $ = id => document.getElementById(id);
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const image = (family, level, form) => form?.image || `/static/stickers/${encodeURIComponent(family)}-${level}.webp`;
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
    const name = family?.player ? (form?.name || family.name) : `${family?.name || copy.family_id} — ${form?.name || copy.family_id}`;
    return `${name} · ${family?.rarity || ''} · Level ${copy.level}`;
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
      html += `<label class="sticker-choice"><input type="radio" name="${name}" value="${escape(copy.id)}" ${optional ? '' : 'required'}><img loading="lazy" src="${escape(image(copy.family_id,copy.level,info(copy).form))}" alt=""><span>${escape(title(copy))}<br><small>${count} available · wager one copy</small></span></label>`;
    }
    if (!groups.size && !optional) html += '<p>No unlocked stickers available. Decline this offer or collect more.</p>';
    return html;
  }
  function renderOdds(odds) {
    const panel = $('sticker-odds');
    if (!panel) return;
    if (!coin || !odds) { panel.textContent = ''; return; }
    const early = odds.warmup ? `Early history: ${odds.flip_count}/100 flips; p-value weighting begins at 100 flips.` : `Entropy ${odds.entropy.toFixed(2)}/8 · p-value ${odds.p_value.toPrecision(3)} · ${odds.flip_count} flips.`;
    const test = odds.includes_test ? ' Test mode — includes test flips; real sticker odds ignore them.' : '';
    panel.textContent = `Current sticker chance: ${(odds.drop_chance*100).toFixed(1)}%. ${early} The next flip can change this chance.${test}`;
  }
  function renderAlbum() {
    const album = $('sticker-album');
    if (!album || !catalog) return;
    const packs = catalog.packs || [{id:'twelve-clans',pack_name:catalog.pack_name,narrative:catalog.narrative,total_forms:catalog.families.length*3}];
    if (!packs.some(pack => pack.id === selectedPack)) selectedPack = catalog.active_pack_id || packs[0].id;
    const pack = packs.find(pack => pack.id === selectedPack);
    $('sticker-title').textContent = pack.pack_name;
    if ($('sticker-lore')) $('sticker-lore').textContent = pack.narrative || '';
    const picker = $('sticker-pack');
    if (picker) {
      picker.innerHTML = packs.map(item => `<option value="${escape(item.id)}">${escape(item.pack_name)}${item.id === catalog.active_pack_id ? ' · current season' : ' · archive'}</option>`).join('');
      picker.value = selectedPack;
    }
    if ($('sticker-search')) $('sticker-search').disabled = !coin;
    const selectedCopies = copies.filter(copy => (copy.pack_id || info(copy).family?.pack_id || 'twelve-clans') === selectedPack);
    const owned = new Set(selectedCopies.map(s => `${s.family_id}:${s.level}`));
    const families = catalog.families.filter(family =>
      (family.pack_id || 'twelve-clans') === selectedPack && selectedCopies.some(copy => copy.family_id === family.id) &&
      String(family.name || family.id).toLocaleLowerCase().includes(search.toLocaleLowerCase()));
    $('sticker-progress').textContent = coin ? `${coin} · ${owned.size}/${pack.total_forms} forms collected · ${selectedCopies.length} ${selectedCopies.length === 1 ? 'copy' : 'copies'}${search ? ` · ${families.length} matching players or families` : ''}` : 'Tap a coin to see its collection.';
    const policy = $('sticker-rarity-policy');
    if (policy) policy.textContent = pack.selection?.type === 'player_weights' ?
      'Rarity is an editorial fan-favorite ranking. Each Common player is twice as likely as each Uncommon player, four times as likely as each Rare player, and eight times as likely as each Legendary player. The complete roster shares the same overall sticker drop chance.' :
      'When a sticker drops in this pack: Common 60%, Uncommon 25%, Rare 12%, Legendary 3%.';
    album.innerHTML = coin ? families.map(family => `<details class="sticker-family" data-family="${escape(family.id)}"><summary>${escape(family.name || family.id)} · <span class="sticker-rarity ${escape(family.rarity)}">${escape(family.rarity)}</span></summary><div class="sticker-grid">${family.forms.filter(form => owned.has(`${family.id}:${form.level}`)).map(form => {
      const matching = copies.filter(s => s.family_id === family.id && s.level === form.level);
      const locked = matching.filter(s => s.locked_challenge_id).length;
      const player = family.player;
      return `<article class="sticker-card${player ? ` sticker-level-${form.level}` : ''}"><div class="sticker-portrait"><img loading="lazy" src="${escape(image(family.id,form.level,form))}" alt="${escape(form.name)}"></div><h4>${escape(form.name)}</h4><div class="sticker-meta"><span class="sticker-rarity ${escape(family.rarity)}">${escape(family.rarity)}</span> · Level ${form.level}${form.treatment ? ` · ${escape(form.treatment)}` : ''}<br>${matching.length} owned${locked ? ` · ${locked} locked in wager` : ''}</div>${player ? playerDetails(family,pack) : `<blockquote>“${escape(form.quote)}”</blockquote>`}</article>`;
    }).join('')}</div></details>`).join('') : '';
    if (coin && !selectedCopies.length) album.innerHTML = '<p>No stickers collected in this pack yet. Flip this coin for a chance to find a current-season sticker.</p>';
    else if (coin && !families.length) album.innerHTML = '<p>No collected stickers match your search.</p>';
  }
  function playerDetails(family, pack) {
    const player = family.player;
    const sections = [];
    for (const competition of ['regular_season','playoffs']) {
      const roles = player.stats?.[competition] || {};
      for (const [role, stats] of Object.entries(roles)) {
        const fields = role === 'goalie' ? [['gamesPlayed','GP'],['wins','W'],['shutouts','SO'],['goalsAgainstAverage','GAA'],['savePct','SV%']] : [['gamesPlayed','GP'],['goals','G'],['assists','A'],['points','P']];
        const cells = fields.map(([key,label]) => {
          const value = stats[key];
          const shown = value == null ? '—' : key === 'savePct' ? Number(value).toFixed(3) : key === 'goalsAgainstAverage' ? Number(value).toFixed(2) : value;
          return `<span><strong>${label}</strong> ${escape(shown)}</span>`;
        }).join('');
        sections.push(`<p class="sticker-stats-label">Rangers NHL ${competition === 'regular_season' ? 'regular season' : 'playoffs'} · ${role === 'goalie' ? 'goalie' : 'skater'}</p><div class="sticker-stat-line">${cells}</div>`);
      }
    }
    const sources = [...new Set([...(player.sources || []),...(player.rarity_sources || [])])].filter(url => {
      try { const source = new URL(url); return source.protocol === 'https:' && /(^|\.)(nhl\.com|nhle\.com)$/.test(source.hostname); } catch { return false; }
    });
    return `<p class="sticker-player-tenure">${escape((player.positions || []).join(' / '))} · ${escape(player.tenure || '')}</p>${sections[0] || ''}<details class="sticker-player-details"><summary>Player details and sources</summary>${sections.slice(1).join('')}${family.art_reference ? `<p class="sticker-art-note">${escape(family.art_reference.note)}</p>` : ''}<p><strong>Fact:</strong> ${escape(family.fact)}</p><p><strong>Original cartoon flavor:</strong> ${escape(family.flavor)}</p><p>${escape(player.rarity_reason || '')}</p><p>Rangers career totals. — means unavailable. Snapshot: ${escape(pack.snapshot || 'not recorded')}.</p><ul>${sources.map((url,index) => `<li><a href="${escape(url)}" target="_blank" rel="noopener noreferrer">Official source ${index+1}</a></li>`).join('')}</ul></details>`;
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
    const terms = stakes.map(s => `<p><img class="sticker-mini" loading="lazy" src="${escape(image(s.family_id,s.level,info(s).form))}" alt="">${escape(s.coin_name)} offers <strong>${escape(title(s))}</strong></p>`).join('');
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
    const query = new URLSearchParams({coin_name:coin});
    const testOutcome = new URLSearchParams(location.search).get('drew_test_outcome');
    if (testOutcome) query.set('drew_test_outcome',testOutcome);
    const response = await fetch('/api/stickers?' + query);
    if (!response.ok) throw new Error('Could not load stickers.');
    const data = await response.json();
    const next = JSON.stringify([data.stickers,data.challenge,data.odds,data.catalog]);
    if (force || next !== signature || !catalog) {
      signature = next; catalog = data.catalog; copies = coin ? data.stickers : []; challenge = data.challenge;
      const open = new Set([...document.querySelectorAll('.sticker-family[open]')].map(el => el.dataset.family));
      renderOdds(data.odds);
      renderAlbum(); document.querySelectorAll('.sticker-family').forEach(el => el.open = open.has(el.dataset.family));
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
    if (award.odds) renderOdds(award.odds);
    const notices = [];
    if (award.drop) notices.push(`Sticker found: ${title(award.drop)}!`);
    for (const event of award.evolutions || []) notices.push(`3 copies combined automatically: ${title(event.sticker)}!`);
    if (notices.length && $('sticker-reveal')) {
      $('sticker-reveal').hidden = false;
      $('sticker-reveal').textContent = notices.join(' ');
      if (award.drop) {
        const thumbnail = document.createElement('img');
        thumbnail.className = 'sticker-mini'; thumbnail.alt = '';
        thumbnail.src = image(award.drop.family_id,award.drop.level,info(award.drop).form);
        $('sticker-reveal').prepend(thumbnail);
      }
    }
    refresh(true).catch(() => {});
  }
  function init(name) {
    coin = name || '';
    $('sticker-pack')?.addEventListener('change',event => { selectedPack = event.target.value; renderAlbum(); });
    $('sticker-search')?.addEventListener('input',event => { search = event.target.value; renderAlbum(); });
    refresh().catch(() => { if ($('sticker-progress')) $('sticker-progress').textContent = 'Collection unavailable. Please refresh to try again.'; });
    if (coin) setInterval(() => { if (!document.hidden && !busy) refresh().catch(() => {}); },3000);
  }
  return {init,appendAuth,onAward,refresh};
})();
