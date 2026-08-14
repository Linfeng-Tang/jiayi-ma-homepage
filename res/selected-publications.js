(() => {
  const list = document.querySelector('#selected-publications-list');
  if (!list) return;
  const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const titleOf = citation => (citation.match(/"(.+?)"/) || [])[1] || citation;
  const scholarSearch = title => `https://scholar.google.com/scholar?q=${encodeURIComponent(`"${title}"`)}`;
  const cleanCitation = citation => citation.replace(/\s*\((?:PDF|Code)\)/gi, '').replace(/\s+\./g, '.').trim();
  const scholarProfile = 'https://scholar.google.com/citations?user=73trMQkAAAAJ&hl=en';

  function actions(paper) {
    const links = [{ label: 'Paper', url: paper.paper || scholarSearch(titleOf(paper.citation)) }];
    if (paper.code) links.push({ label: 'Code', url: paper.code });
    if (Number(paper.citations) > 100) links.push({ label: `${Number(paper.citations).toLocaleString()} citations`, url: scholarProfile, citation: true });
    const seen = new Set();
    const actions = links.filter(link => link.url && !seen.has(link.url) && seen.add(link.url)).map(link =>
      `<a class="res-chip${link.citation ? ' cite-badge' : ''}" href="${escapeHTML(link.url)}" target="_blank" rel="noreferrer">${escapeHTML(link.label)}</a>`
    ).join('');
    const esi = [
      paper.esiHighlyCited && '<span class="res-chip esi-badge esi-high">ESI Highly Cited Paper</span>',
      paper.esiHot && '<span class="res-chip esi-badge esi-hot">ESI Hot Paper</span>'
    ].filter(Boolean).join('');
    return actions + esi;
  }

  fetch('res/publications.json', { cache: 'no-store' }).then(response => response.ok ? response.json() : Promise.reject()).then(data => {
    // Publications are ordered newest first. Keep the first matching title so
    // journal extensions (e.g. ConvMatch in IEEE TPAMI) take precedence over
    // their earlier conference versions with the same title.
    const byTitle = new Map();
    data.publications.forEach(paper => {
      const title = titleOf(paper.citation);
      if (!byTitle.has(title)) byTitle.set(title, paper);
    });
    const selected = (data.selectedTitles || []).map(title => byTitle.get(title)).filter(Boolean);
    list.innerHTML = selected.map(paper => `<li><p>${escapeHTML(cleanCitation(paper.citation))}</p><p class="paper-actions">${actions(paper)}</p></li>`).join('');
  }).catch(() => { list.innerHTML = '<li>Selected publications are temporarily unavailable.</li>'; });
})();
