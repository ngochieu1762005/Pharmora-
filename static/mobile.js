'use strict';
/* Small-screen interaction enhancements; no external dependencies. */
(() => {
  const menuBtn=document.getElementById('mobileMenuBtn');
  const menu=document.getElementById('mobileNav');
  if(menuBtn&&menu){
    document.addEventListener('click',e=>{
      if(!menu.hidden&&!menu.contains(e.target)&&!menuBtn.contains(e.target)){
        menu.hidden=true;menuBtn.setAttribute('aria-expanded','false');
      }
    });
  }
  const toggle=document.getElementById('menuToggle');
  const sidebar=document.getElementById('sidebar');
  const shade=document.getElementById('mobileShade');
  const modalHost=document.getElementById('modalHost');
  const syncDrawer=()=>{
    const open=!!sidebar?.classList.contains('open');
    document.body.classList.toggle('ws-drawer-open',open);
    if(toggle)toggle.setAttribute('aria-expanded',String(open));
    if(shade)shade.setAttribute('aria-hidden',String(!open));
  };
  if(sidebar){
    new MutationObserver(syncDrawer).observe(sidebar,{attributes:true,attributeFilter:['class']});
    syncDrawer();
    if(toggle)toggle.setAttribute('aria-controls','sidebar');
    sidebar.setAttribute('aria-label','Điều hướng workspace');
  }
  const closeDrawer=()=>{
    sidebar?.classList.remove('open');shade?.classList.remove('open');syncDrawer();
  };
  const syncModal=()=>{
    document.body.classList.toggle('ws-modal-open',!!modalHost?.querySelector('.ws-overlay'));
  };
  if(modalHost){
    new MutationObserver(syncModal).observe(modalHost,{childList:true});
    syncModal();
  }
  document.addEventListener('keydown',e=>{
    if(e.key!=='Escape')return;
    if(menu&&!menu.hidden){menu.hidden=true;menuBtn?.setAttribute('aria-expanded','false');}
    if(sidebar?.classList.contains('open'))closeDrawer();
    if(modalHost?.querySelector('.ws-overlay'))document.getElementById('modalClose')?.click();
  });
  // Tables are populated dynamically by workspace.js. Label every cell so on
  // narrow screens rows can become readable cards without horizontal zoom.
  const workspace=document.getElementById('workspaceContent');
  if(workspace){
    let queued=false;
    const annotate=()=>{
      queued=false;
      workspace.querySelectorAll('.ws-table').forEach(table=>{
        const labels=[...table.querySelectorAll('thead th')].map(th=>th.textContent.trim());
        if(!labels.length)return;
        table.querySelectorAll('tbody tr').forEach(row=>{
          [...row.children].forEach((cell,i)=>{
            if(cell.tagName!=='TD'||cell.hasAttribute('colspan'))return;
            cell.dataset.label=labels[i]||'THÔNG TIN';
          });
        });
      });
    };
    new MutationObserver(()=>{
      if(queued)return;
      queued=true;requestAnimationFrame(annotate);
    }).observe(workspace,{childList:true,subtree:true});
    annotate();
  }
})();
