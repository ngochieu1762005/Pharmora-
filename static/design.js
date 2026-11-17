'use strict';
/*
 * PharmaVision 3.0 progressive interaction enhancements.
 * Works with the existing API, desktop/sidebar navigation, and Mobile 2.0.
 * No external libraries or authentication changes.
 */
(() => {
  const $ = selector => document.querySelector(selector);
  const $$ = selector => [...document.querySelectorAll(selector)];
  const previewDate = $('.preview-date');
  if (previewDate) {
    previewDate.textContent = new Intl.DateTimeFormat('vi-VN', {
      day:'numeric', month:'long', year:'numeric'
    }).format(new Date());
  }

  const headerDate = $('#headerDate');
  if (headerDate) {
    headerDate.textContent = new Intl.DateTimeFormat('vi-VN', {
      weekday:'long', day:'numeric', month:'long'
    }).format(new Date());
  }

  const trigger = $('#headerQuickSearch');
  const quickSale = $('#headerQuickSale');
  const sidebar = $('#sidebar');
  if (!sidebar) return;

  const navigation = [
    {page:'overview',name:'Tổng quan',hint:'Doanh thu, cảnh báo, hoạt động'},
    {page:'inventory',name:'Quản lý kho',hint:'Danh mục thuốc, lô, hạn dùng'},
    {page:'sales',name:'Bán thuốc',hint:'Đơn bán và giỏ hàng'},
    {page:'copilot',name:'Trợ lý dược sĩ',hint:'Tra cứu dữ liệu nhà thuốc'},
    {page:'forecast',name:'Dự báo nhu cầu',hint:'Kế hoạch nhập hàng'},
    {page:'alerts',name:'Rủi ro và thu hồi',hint:'Tồn thấp, lô gần hạn'},
    {page:'customers',name:'Khách hàng',hint:'Hồ sơ và sự đồng ý'},
    {page:'history',name:'Lịch sử bán hàng',hint:'Giao dịch đã lưu'},
    {page:'settings',name:'Cài đặt',hint:'Nhân viên, tài khoản, quyền'}
  ];
  const entries = navigation.filter(item => sidebar.querySelector('[data-page="' + item.page + '"]'));

  function navigate(page) {
    const button = sidebar.querySelector('[data-page="' + page + '"]');
    if (!button) return;
    const close = $('#modalClose');
    if (close && $('#pvCommandInput')) close.click();
    button.click();
    const main = $('#workspaceContent');
    if (main) main.setAttribute('tabindex','-1');
  }

  function safeText(value) {
    return String(value).replace(/[&<>"']/g, ch => ({
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
    }[ch]));
  }

  function openSearch() {
    // Don't dismiss an unfinished form modal.
    if ($('#overlay') || typeof window.showModal !== 'function') return;
    window.showModal('Tìm nhanh trong hệ thống',
      '<label for="pvCommandInput" class="pv-command-hint">Tìm tính năng bạn muốn sử dụng</label>' +
      '<input class="pv-command-input" id="pvCommandInput" type="search" autocomplete="off" ' +
      'placeholder="Ví dụ: bán thuốc, tồn kho, khách hàng…" aria-label="Tìm tính năng">' +
      '<div id="pvCommandResults" class="pv-command-results" role="list"></div>' +
      '<p class="pv-command-hint">Nhấn Enter để mở kết quả đầu tiên · Esc để đóng</p>',
      () => {
        const input = $('#pvCommandInput');
        const output = $('#pvCommandResults');
        const update = () => {
          const term = input.value.trim().toLocaleLowerCase('vi');
          const matched = entries.filter(x => (
            (x.name + ' ' + x.hint).toLocaleLowerCase('vi').includes(term)
          ));
          output.innerHTML = matched.length
            ? matched.map(x =>
                '<button type="button" class="pv-command-item" data-command-page="' + x.page + '">' +
                safeText(x.name) + '<span aria-hidden="true">↗</span></button>'
              ).join('')
            : '<div class="pv-command-empty">Không tìm thấy tính năng phù hợp.</div>';
          $$('[data-command-page]').forEach(btn => {
            btn.addEventListener('click', () => navigate(btn.dataset.commandPage));
          });
          input.dataset.firstResult = matched[0]?.page || '';
        };
        input.addEventListener('input',update);
        input.addEventListener('keydown',e=>{
          if (e.key==='Enter' && input.dataset.firstResult) {
            e.preventDefault();
            navigate(input.dataset.firstResult);
          }
        });
        update();
        input.focus();
      }
    );
  }

  if (trigger) trigger.addEventListener('click',openSearch);
  if (quickSale) quickSale.addEventListener('click',()=>navigate('sales'));
  document.addEventListener('keydown', event => {
    const key = String(event.key).toLowerCase();
    if ((event.ctrlKey || event.metaKey) && key === 'k') {
      event.preventDefault();
      openSearch();
    }
    if (key === 'escape' && $('#pvCommandInput')) {
      $('#modalClose')?.click();
    }
  });

  // The visual current-page indicator comes from the existing workspaces.
  // Never change data-page or API state in this enhancement layer.
})();
