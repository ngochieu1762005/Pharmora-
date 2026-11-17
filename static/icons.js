'use strict';
/*
 * PharmaVision Iconography 1.0
 * Inline SVG icons (24x24, round strokes, currentColor). Icon-only
 * placeholders are progressively replaced; the application remains
 * functional without JavaScript-generated icons.
 *
 * Lucide-inspired pictograms. Lucide is ISC licensed:
 * https://lucide.dev/license — copyright Lucide Icons contributors.
 */
(() => {
  const NS='http://www.w3.org/2000/svg';
  const paths={
    medical:'<path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6z"/>',
    overview:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    inventory:'<path d="m3 7 9-4 9 4v11l-9 4-9-4V7Z"/><path d="m3 7 9 4 9-4M12 11v11"/>',
    sales:'<circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M2 3h2l2.4 12h12.2l2-8H5"/>',
    copilot:'<path d="m12 3 1.9 6.1L20 11l-6.1 1.9L12 19l-1.9-6.1L4 11l6.1-1.9L12 3ZM20 17l.7 1.6L22 19l-1.3.4L20 21l-.7-1.6L18 19l1.3-.4L20 17Z"/>',
    forecast:'<path d="M3 3v18h18"/><path d="m7 16 4-5 3 2 6-8"/><path d="M16 5h4v4"/>',
    alerts:'<path d="M12 3 2 20h20L12 3Z"/><path d="M12 9v4m0 4h.01"/>',
    customers:'<circle cx="9" cy="8" r="3"/><path d="M2 20v-2c0-3 3-5 7-5s7 2 7 5v2"/><path d="M17 11a3 3 0 0 0 0-6m1 8c3 0 4 2 4 5v2"/>',
    history:'<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l4 2"/>',
    settings:'<circle cx="12" cy="12" r="3"/><path d="M19.4 15.1 21 16l-2 3.4-1.9-.8A8 8 0 0 1 14 20l-.4 2h-3.5l-.4-2A8 8 0 0 1 6.7 18.6l-1.9.8L2.8 16l1.6-.9a8 8 0 0 1 0-3.2L2.8 11l2-3.4 1.9.8A8 8 0 0 1 9.7 7l.4-2h3.5l.4 2a8 8 0 0 1 3.1 1.4l1.9-.8 2 3.4-1.6.9a8 8 0 0 1 0 3.2Z"/>',
    arrow:'<path d="M7 17 17 7M8 7h9v9"/>',
    arrowRight:'<path d="M5 12h14m-6-6 6 6-6 6"/>',
    arrowDown:'<path d="M12 3v17m-6-6 6 6 6-6"/>',
    plus:'<path d="M12 5v14M5 12h14"/>',
    download:'<path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4"/>',
    upload:'<path d="M12 21V9m-5 5 5-5 5 5M4 7V3h16v4"/>',
    scan:'<path d="M8 3H5a2 2 0 0 0-2 2v3m13-5h3a2 2 0 0 1 2 2v3M3 16v3a2 2 0 0 0 2 2h3m13-5v3a2 2 0 0 1-2 2h-3M7 12h10M8 9v6m3-6v6m3-6v6m2-6v6"/>',
    camera:'<path d="M4 6h4l2-2h4l2 2h4v14H4V6Z"/><circle cx="12" cy="13" r="4"/>',
    search:'<circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/>',
    check:'<path d="m4 12 5 5L20 6"/>',
    shield:'<path d="m12 2 9 4v6c0 5.3-3.7 8.7-9 10-5.3-1.3-9-4.7-9-10V6l9-4Z"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
    clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    trend:'<path d="m3 17 6-6 4 4 8-8m-5 0h5v5"/>',
    user:'<circle cx="12" cy="8" r="4"/><path d="M4 21v-2c0-4 3-6 8-6s8 2 8 6v2"/>',
    clipboard:'<rect x="5" y="5" width="14" height="17" rx="2"/><path d="M9 5V3h6v2m-6 6h6m-6 4h6"/>',
    info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-9h.01"/>',
    logout:'<path d="M10 4H4v16h6m5-4 4-4-4-4m-9 4h13"/>',
    file:'<path d="M6 2h8l5 5v15H6V2Z"/><path d="M14 2v5h5m-9 5h5m-5 4h5"/>',
    play:'<path d="m8 5 11 7-11 7V5Z"/>',
    save:'<path d="M4 3h15l2 2v16H3V3h1Z"/><path d="M7 3v6h10V3M7 21v-8h10v8"/>',
    minus:'<path d="M5 12h14"/>',
    globe:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c6 6 6 12 0 18M12 3c-6 6-6 12 0 18"/>',
    lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    menu:'<path d="M4 6h16M4 12h16M4 18h16"/>'
  };
  const glyphs={'＋':'plus','+':'plus','↓':'download','↗':'arrow','→':'arrowRight','◉':'camera','▦':'scan','▣':'inventory','▤':'clipboard','♧':'sales','✳':'copilot','◷':'clock','↪':'logout','✓':'check','◎':'overview','✦':'copilot'};
  function svg(name) {
    const root=document.createElementNS(NS,'svg');
    root.setAttribute('viewBox','0 0 24 24');
    root.setAttribute('fill','none');
    root.setAttribute('stroke','currentColor');
    root.setAttribute('stroke-width','1.9');
    root.setAttribute('stroke-linecap','round');
    root.setAttribute('stroke-linejoin','round');
    root.setAttribute('aria-hidden','true');
    root.setAttribute('focusable','false');
    root.classList.add('pv-icon');
    root.innerHTML=paths[name]||paths.info;
    return root;
  }
  function slot(el,name) {
    if (!el||el.dataset.pvIconReady) return;
    el.replaceChildren(svg(name));
    el.dataset.pvIconReady='1';
  }
  function keyed(selector, mapping, parent=document) {
    Object.entries(mapping).forEach(([key,icon])=>{
      parent.querySelectorAll(selector.replace('%s',key)).forEach(el=>slot(el,icon));
    });
  }
  function cleanGlyph(node, atStart) {
    if (!node || node.nodeType!==3) return null;
    const text=node.nodeValue||'';
    const match=atStart ? text.match(/^\s*([＋+↓↗→◉▦▣▤♧✳◷↪✓◎✦])\s*/) :
                          text.match(/\s*([↗→])\s*$/);
    if (!match||!glyphs[match[1]]) return null;
    node.nodeValue=atStart?text.slice(match[0].length):text.slice(0,text.length-match[0].length);
    return glyphs[match[1]];
  }
  function action(el) {
    if (el.dataset.pvActionReady) return;
    el.dataset.pvActionReady='1';
    const children=[...el.childNodes];
    // Handles labels like "＋ Thêm thuốc" and "↓ Xuất CSV" without altering their actual text.
    const first=children.find(n=>n.nodeType===3&&n.nodeValue.trim());
    const leading=cleanGlyph(first,true);
    if(leading)el.insertBefore(svg(leading),first);
    const last=[...el.childNodes].reverse().find(n=>n.nodeType===3&&n.nodeValue.trim());
    const trailing=cleanGlyph(last,false);
    if(trailing)el.appendChild(svg(trailing));
    // Existing CTA arrows are separate spans. Swap content but preserve
    // span and accessible link title.
    [...el.children].filter(x=>x.tagName==='SPAN'&&!x.classList.contains('pv-icon')).forEach(span=>{
      const only=span.textContent.trim();
      if(glyphs[only]&&span.children.length===0)slot(span,glyphs[only]);
    });
  }
  const navIcons={overview:'overview',inventory:'inventory',sales:'sales',copilot:'copilot',forecast:'forecast',alerts:'alerts',customers:'customers',history:'history',settings:'settings'};
  const featureIcons=['inventory','clock','forecast','customers','scan','shield'];
  const bandIcons=['medical','inventory','copilot','customers'];
  const statsByText=[
    [/doanh thu/i,'trend'],
    [/đơn bán|đơn hàng/i,'sales'],
    [/sản phẩm|danh mục|tổng tồn|kho/i,'inventory'],
    [/cảnh báo|sắp hết|gần hết hạn|tồn thấp/i,'alerts']
  ];
  function enhance() {
    document.querySelectorAll('.logo-icon').forEach(el=>slot(el,'medical'));
    keyed('.ws-nav button[data-page="%s"] .nav-ic',navIcons);
    document.querySelectorAll('.ws-pharmacy .ph-ic').forEach(el=>slot(el,'medical'));
    document.querySelectorAll('.feature-card .feature-ic').forEach((el,i)=>slot(el,featureIcons[i]||'medical'));
    document.querySelectorAll('.band-items i').forEach((el,i)=>slot(el,bandIcons[i]||'medical'));
    document.querySelectorAll('.float-icon').forEach((el,i)=>slot(el,i===0?'alerts':'check'));
    document.querySelectorAll('.register-benefits span').forEach(el=>slot(el,'check'));
    document.querySelectorAll('.security-icon-large').forEach(el=>slot(el,'shield'));
    document.querySelectorAll('.trust-avatars span').forEach(el=>{if(el.textContent.trim()==='✓')slot(el,'check')});
    document.querySelectorAll('.timeline-row>span,.solution-number>span').forEach(el=>slot(el,'arrow'));
    document.querySelectorAll('.ws-stat .stat-symbol').forEach(el=>{
      const label=el.closest('.ws-stat')?.querySelector('small')?.textContent||'';
      slot(el,statsByText.find(x=>x[0].test(label))?.[1]||'overview');
    });
    document.querySelectorAll('.ws-alert-row .alert-symbol').forEach(el=>{
      slot(el,el.classList.contains('danger')?'alerts':el.textContent.includes('✓')?'check':'clock');
    });
    document.querySelectorAll('.ws-overview-intro .hello-icon').forEach(el=>slot(el,'medical'));
    document.querySelectorAll('.ws-header-button#headerQuickSearch>span:first-child').forEach(el=>slot(el,'search'));
    document.querySelectorAll('.security-points span').forEach(el=>{
      if(el.dataset.pvCheckReady)return;
      const node=[...el.childNodes].find(n=>n.nodeType===3&&n.nodeValue.trim());
      if(node&&node.nodeValue.trim().startsWith('✓')) {
        const name=cleanGlyph(node,true);
        if(name)el.insertBefore(svg(name),node);
      }
      el.dataset.pvCheckReady='1';
    });
    document.querySelectorAll('a.btn,button.btn,button.ws-btn,button.ws-small-button,.sidebar-bottom button.small-link,.ws-header-button').forEach(action);
    document.querySelectorAll('.play-circle').forEach(el=>slot(el,'play'));
    document.querySelectorAll('.ws-banner .pv-icon').forEach(el=>el.setAttribute('aria-hidden','true'));
  }

  let pending=false;
  function queue() {
    if(pending)return;
    pending=true;
    requestAnimationFrame(()=>{pending=false;enhance()});
  }
  // Dynamic table/modal content is generated using innerHTML by workspace.js.
  // Observe only relevant application roots, avoiding work on unrelated DOM.
  const roots=[document.getElementById('workspaceContent'),document.getElementById('modalHost'),document.getElementById('sidebar')].filter(Boolean);
  roots.forEach(root=>new MutationObserver(queue).observe(root,{subtree:true,childList:true}));
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',enhance,{once:true});
  else enhance();
})();
