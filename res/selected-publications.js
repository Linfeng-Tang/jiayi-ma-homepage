(() => {
  const selectedTitles = [
    'GText-IF: Leveraging Text-Driven Semantics for Degradation-Aware Image Fusion',
    'Locality Optimization Refinement with Deformation for Shape Matching via Functional Maps',
    'Mask-DiFuser: A Masked Diffusion Model for Unified Unsupervised Image Fusion',
    'ControlFusion: A Controllable Image Fusion Network with Language-Vision Degradation Prompts',
    'DeMatch++: Two-View Correspondence Learning via Deep Motion Field Decomposition and Respective Local-Context Aggregation',
    'OmniFuse: Composite Degradation-Robust Image Fusion with Language-Driven Semantics',
    'Diff-Retinex++: Retinex-Driven Reinforced Diffusion Model for Low-Light Image Enhancement',
    'C2RF: Bridging Multi-modal Image Registration and Fusion via Commonality Mining and Contrastive Learning',
    'Feature Matching via Graph Clustering with Local Affine Consensus',
    'Spatiotemporal modeling of molecular holograms',
    'U-Match: Exploring Hierarchy-aware Local Context for Two-view Correspondence Learning',
    'CRetinex: A Progressive Color-shift Aware Retinex Model for Low-light Image Enhancement',
    'ConvMatch: Rethinking Network Design for Two-View Correspondence Learning',
    'Robust Model Reasoning and Fitting via Dual Sparsity Pursuit',
    'STP-SOM: Scale-transfer Learning for Pansharpening via Estimating Spectral Observation Model',
    'MURF: Mutually Reinforcing Multi-modal Image Registration and Fusion',
    'Efficient Deterministic Search with Robust Loss Functions for Geometric Model Fitting',
    'Feature Matching via Motion-Consistency Driven Probabilistic Graphical Model',
    'SwinFusion: Cross-domain Long-range Learning for General Image Fusion via Swin Transformer',
    'Image fusion in the loop of high-level vision tasks: A semantic-aware real-time infrared and visible image fusion network',
    'A Progressive Fusion Generative Adversarial Network for Realistic and Consistent Video Super-Resolution',
    'U2Fusion: A Unified Unsupervised Image Fusion Network',
    'SDNet: A Versatile Squeeze-and-Decomposition Network for Real-Time Image Fusion',
    'Beyond Brightening Low-light Images',
    'Image Matching from Handcrafted to Deep Features: A Survey',
    'DDcGAN: A Dual-discriminator Conditional Generative Adversarial Network for Multi-resolution Image Fusion',
    'FusionGAN: A generative adversarial network for infrared and visible image fusion',
    'Locality Preserving Matching',
    'Robust Point Matching via Vector Field Consensus',
    'Robust Estimation of Nonrigid Transformation for Point Set Registration'
  ];
  const list = document.querySelector('#selected-publications-list');
  if (!list) return;
  const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const titleOf = citation => (citation.match(/"(.+?)"/) || [])[1] || citation;
  const scholarSearch = title => `https://scholar.google.com/scholar?q=${encodeURIComponent(`"${title}"`)}`;
  const cleanCitation = citation => citation.replace(/\s*\(Code\)/gi, '').replace(/\s+\./g, '.').trim();
  const scholarProfile = 'https://scholar.google.com/citations?user=73trMQkAAAAJ&hl=en';

  function actions(paper) {
    const links = [{ label: 'Paper', url: paper.paper || scholarSearch(titleOf(paper.citation)) }];
    if (paper.code) links.push({ label: 'Code', url: paper.code });
    if (Number(paper.citations) > 100) links.push({ label: `${Number(paper.citations).toLocaleString()} citations`, url: scholarProfile, citation: true });
    const seen = new Set();
    return links.filter(link => link.url && !seen.has(link.url) && seen.add(link.url)).map(link =>
      `<a class="res-chip${link.citation ? ' cite-badge' : ''}" href="${escapeHTML(link.url)}" target="_blank" rel="noreferrer">${escapeHTML(link.label)}</a>`
    ).join('');
  }

  fetch('res/publications.json', { cache: 'no-store' }).then(response => response.ok ? response.json() : Promise.reject()).then(data => {
    const byTitle = new Map(data.publications.map(paper => [titleOf(paper.citation), paper]));
    const selected = selectedTitles.map(title => byTitle.get(title)).filter(Boolean);
    list.innerHTML = selected.map(paper => `<li><p>${escapeHTML(cleanCitation(paper.citation))}</p><p class="paper-actions">${actions(paper)}</p></li>`).join('');
  }).catch(() => { list.innerHTML = '<li>Selected publications are temporarily unavailable.</li>'; });
})();
