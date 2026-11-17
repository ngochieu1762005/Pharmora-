'use strict';
/* PharmaVision Mobile 2.0: mobile-only navigation, tables, dialog accessibility.
   Desktop features are unaffected; this script contains no dependencies. */
(() => {
  const q=(sel,root=document)=>root.querySelector(sel);
  const qa=(sel,root=document)=>[...root.querySelectorAll(sel)];
  const isMobile=()=>window.matchMedia('(max-width: 900px)').matches;

  /* Landing navigation remains driven by site.js; keep its state consistent. */
  const siteMenu=q('#mobileNav');
  const siteToggle=q('#mobileMenuBtn');
  const closeSiteMenu=()=>{
    if(!siteMenu||!siteToggle)return;
    siteMenu.hidden=true;
    siteToggle.setAttribute('aria-expanded','false');
  };
  if(siteMenu&&siteToggle){
    siteToggle.setAttribute('aria-controls','mobileNav');
    document.addEventListener('pointerdown',e=>{
      if(!siteMenu.hidden&&!siteMenu.contains(e.target)&&!siteToggle.contains(e.target))closeSiteMenu();
    });
    qa('a',siteMenu).forEach(link=>link.addEventListener('click',closeSiteMenu));
  }

  const sidebar=q('#sidebar');
  const shade=q('#mobileShade');
  const toggle=q('#menuToggle');
  const closeButton=q('#sidebarClose');
  const dock=q('#mobileBottomNav');
  const more=q('#mobileMore');
  const modalHost=q('#modalHost');
  const workspace=q('#workspaceContent');

  const closeDrawer=()=>{
    sidebar?.classList.remove('open');
    shade?.classList.remove('open');
    syncDrawer();
  };
  const syncDrawer=()=>{
    const open=Boolean(sidebar?.classList.contains('open'));
    document.body.classList.toggle('ws-drawer-open',open&&isMobile());
    if(toggle)toggle.setAttribute('aria-expanded',String(open));
    if(more)more.setAttribute('aria-expanded',String(open));
    if(shade)shade.setAttribute('aria-hidden',String(!open));
  };
  if(sidebar){
    sidebar.setAttribute('aria-label','Điều hướng không gian quản lý');
    if(toggle){toggle.setAttribute('aria-controls','sidebar');toggle.setAttribute('aria-expanded','false');}
    if(more){more.setAttribute('aria-controls','sidebar');more.setAttribute('aria-expanded','false');}
    closeButton?.addEventListener('click',closeDrawer);
    new MutationObserver(syncDrawer).observe(sidebar,{attributes:true,attributeFilter:['class']});
    syncDrawer();
  }

  /* Fixed bottom navigation: delegate to the existing, tested changePage flow. */
  const syncDock=()=>{
    if(!dock)return;
    const selected=q('#sidebar [data-page].active')?.dataset.page||'overview';
    qa('[data-mobile-page]',dock).forEach(button=>{
      const active=button.dataset.mobilePage===selected;
      button.classList.toggle('active',active);
      if(active)button.setAttribute('aria-current','page');
      else button.removeAttribute('aria-current');
    });
  };
  if(dock){
    qa('[data-mobile-page]',dock).forEach(button=>{
      button.addEventListener('click',()=>{
        const page=button.dataset.mobilePage;
        const source=qa('#sidebar [data-page]').find(b=>b.dataset.page===page);
        if(source)source.click();
        closeDrawer();
        syncDock();
      });
    });
    more?.addEventListener('click',()=>{
      if(toggle)toggle.click();
      else {
        sidebar?.classList.toggle('open');
        shade?.classList.toggle('open');
      }
      syncDrawer();
    });
    // The old navigation updates active classes; observe those class changes.
    const nav=q('#sidebar .ws-nav');
    if(nav)new MutationObserver(syncDock).observe(nav,{subtree:true,attributes:true,attributeFilter:['class']});
    syncDock();
  }

  /* Mobile dialogs and keyboard: prevent the bottom bar covering form fields. */
  if(modalHost){
    const syncModal=()=>{
      const open=Boolean(q('.ws-overlay',modalHost));
      document.body.classList.toggle('ws-modal-open',open&&isMobile());
      if(dock)dock.setAttribute('aria-hidden',String(open));
    };
    new MutationObserver(syncModal).observe(modalHost,{childList:true});
    syncModal();
  }
  if(workspace){
    let queued=false;
    const decorateTables=()=>{
      queued=false;
      qa('.ws-table',workspace).forEach(table=>{
        const headings=qa('thead th',table).map(th=>th.textContent.trim());
        if(!headings.length)return;
        qa('tbody tr',table).forEach(row=>{
          [...row.children].forEach((cell,index)=>{
            if(cell.tagName!=='TD'||cell.hasAttribute('colspan'))return;
            cell.dataset.label=headings[index]||'';
          });
        });
      });
    };
    new MutationObserver(()=>{
      if(queued)return;
      queued=true;
      requestAnimationFrame(decorateTables);
    }).observe(workspace,{childList:true,subtree:true});
    decorateTables();
  }

  /* Hide the dock while an on-screen keyboard is likely to be open. */
  if(dock){
    const editable=el=>el?.matches?.('input:not([type="checkbox"]):not([type="radio"]),textarea,select,[contenteditable="true"]');
    const syncEditing=()=>{
      document.body.classList.toggle('ws-keyboard-active',Boolean(isMobile()&&editable(document.activeElement)));
    };
    document.addEventListener('focusin',syncEditing);
    document.addEventListener('focusout',()=>requestAnimationFrame(syncEditing));
    window.addEventListener('pagehide',()=>document.body.classList.remove('ws-keyboard-active'));
  }

  document.addEventListener('keydown',event=>{
    if(event.key!=='Escape')return;
    if(siteMenu&&!siteMenu.hidden)closeSiteMenu();
    if(sidebar?.classList.contains('open'))closeDrawer();
    if(modalHost&&q('.ws-overlay',modalHost))q('#modalClose')?.click();
  });
  window.addEventListener('resize',()=>{
    if(!isMobile()){
      closeDrawer();
      document.body.classList.remove('ws-modal-open','ws-keyboard-active');
    }else{
      syncDrawer();
    }
  });
})();
