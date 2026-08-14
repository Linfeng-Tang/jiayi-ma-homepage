(() => {
  const list = document.querySelector('#publication-list');
  const search = document.querySelector('#publication-search');
  const status = document.querySelector('#publication-status');
  const empty = document.querySelector('#publication-empty');
  const scholarProfile = 'https://scholar.google.com/citations?user=73trMQkAAAAJ&hl=en';
  const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const titleOf = citation => (citation.match(/"(.+?)"/) || [])[1] || citation;
  const cleanCitation = citation => citation.replace(/\s*\((?:PDF|Code)\)/gi, '').replace(/\s+\./g, '.').trim();
  const scholarSearch = title => `https://scholar.google.com/scholar?q=${encodeURIComponent(`"${title}"`)}`;

  function linksFor(paper) {
    const links = [{ label: 'Paper', url: paper.paper || scholarSearch(titleOf(paper.citation)) }];
    if (paper.code) links.push({ label: 'Code', url: paper.code });
    if (Number(paper.citations) > 100) links.push({ label: `${Number(paper.citations).toLocaleString()} citations`, url: scholarProfile, citations: true });
    const seen = new Set();
    return links.filter(link => link.url && !seen.has(link.url) && seen.add(link.url)).map(link =>
      `<a class="res-chip${link.citations ? ' cite-badge' : ''}" href="${escapeHTML(link.url)}" target="_blank" rel="noreferrer">${escapeHTML(link.label)}</a>`
    ).join('');
  }

  function render(publications, query = '') {
    const needle = query.trim().toLowerCase();
    const filtered = publications.filter(paper => `${paper.year} ${paper.citation}`.toLowerCase().includes(needle));
    const groups = filtered.reduce((result, paper) => { (result[paper.year] ||= []).push(paper); return result; }, {});
    let number = 0;
    list.innerHTML = Object.entries(groups).sort(([a], [b]) => Number(b) - Number(a)).map(([year, papers]) => `
      <section class="publication-year"><h3>Year ${year}<span>${papers.length} papers</span></h3><ol>
      ${papers.map(paper => `<li value="${++number}"><p>${escapeHTML(cleanCitation(paper.citation))}</p><p class="paper-actions">${linksFor(paper)}</p></li>`).join('')}
      </ol></section>`).join('');
    empty.hidden = filtered.length > 0;
  }

  fetch('res/publications.json', { cache: 'no-store' }).then(response => {
    if (!response.ok) throw new Error('Publication data unavailable');
    return response.json();
  }).then(data => {
    render(data.publications);
    status.textContent = `${data.publications.length} papers · updated ${new Date(data.syncedAt).toLocaleDateString('en', { year: 'numeric', month: 'short', day: 'numeric' })}`;
    search.addEventListener('input', () => render(data.publications, search.value));
  }).catch(() => { status.textContent = 'Publication data is temporarily unavailable.'; });
})();
