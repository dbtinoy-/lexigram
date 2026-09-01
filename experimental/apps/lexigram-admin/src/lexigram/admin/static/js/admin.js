/**
 * Lexigram Admin - Core JavaScript
 */
(function() {
  'use strict';

  // Initialize admin when DOM is ready
  document.addEventListener('DOMContentLoaded', function() {
    initSidebar();
    initToasts();
    initModals();
    initForms();
    initKeyboardShortcuts();
  });

  // ========== Bulk export download (B28) ==========
  // Export buttons render onclick="return window.LexigramDownloadBulk(this)"
  // with data-bulk-download-url / data-bulk-action attributes. CSV/JSON
  // responses carry Content-Disposition and must bypass HTMX (whose swap
  // would inject the file into the page), so we fetch and download a blob.
  window.LexigramDownloadBulk = function(btn) {
    downloadBulk(btn);
    return false;
  };

  async function downloadBulk(btn) {
    function toast(message, type) {
      if (window.showToast) window.showToast(message, type);
    }
    try {
      const url = btn.getAttribute('data-bulk-download-url');
      if (!url) return;
      const action = btn.getAttribute('data-bulk-action') || 'export';
      const checked = document.querySelectorAll('input[name="ids"]:checked');
      if (!checked.length) {
        toast('Select at least one row to export.', 'warning');
        return;
      }
      const body = new FormData();
      body.append('action', action);
      checked.forEach(function(box) { body.append('ids', box.value); });
      const csrfInput = document.querySelector('input[name="csrf_token"]');
      const csrfEl = document.querySelector('[data-csrf-token]');
      const csrf = window.__lexigramCsrfToken ||
        (csrfInput && csrfInput.value) ||
        (csrfEl && csrfEl.getAttribute('data-csrf-token'));
      if (csrf) body.append('csrf_token', csrf);
      const headers = {};
      if (csrf) headers['X-CSRF-Token'] = csrf;

      const response = await fetch(url, {
        method: 'POST',
        body: body,
        headers: headers,
        credentials: 'same-origin'
      });
      if (!response.ok) {
        toast('Export failed (' + response.status + ').', 'error');
        return;
      }
      const blob = await response.blob();
      const disposition = response.headers.get('Content-Disposition') || '';
      const match = disposition.match(/filename="?([^";]+)"?/i);
      const filename = match ? match[1] : 'export.csv';
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(function() { URL.revokeObjectURL(link.href); }, 4000);
      toast('Exported ' + checked.length + ' record' + (checked.length === 1 ? '' : 's') + '.', 'success');
    } catch (err) {
      toast('Export failed.', 'error');
    }
  }

  // ========== Sidebar ==========
  function initSidebar() {
    const sidebar = document.querySelector('.admin-sidebar');
    const toggle = document.querySelector('[data-toggle="sidebar"]');
    const menuItems = document.querySelectorAll('.sidebar-menu-item');
    
    if (toggle && sidebar) {
      toggle.addEventListener('click', function() {
        document.body.classList.toggle('sidebar-collapsed');
        localStorage.setItem('sidebarCollapsed', 
          document.body.classList.contains('sidebar-collapsed'));
      });
    }
    
    // Restore sidebar state
    if (localStorage.getItem('sidebarCollapsed') === 'true') {
      document.body.classList.add('sidebar-collapsed');
    }
    
    // Submenu toggles
    menuItems.forEach(function(item) {
      const submenu = item.querySelector('.sidebar-submenu');
      if (submenu) {
        const link = item.querySelector('.sidebar-link');
        link.addEventListener('click', function(e) {
          if (submenu) {
            e.preventDefault();
            item.classList.toggle('open');
          }
        });
      }
    });
  }

  // ========== Toast Notifications ==========
  function initToasts() {
    window.showToast = function(message, type, duration) {
      type = type || 'info';
      duration = duration || 3000;
      
      const container = document.querySelector('.toast-container') || createToastContainer();
      const toast = document.createElement('div');
      toast.className = 'toast toast-' + type;
      toast.innerHTML = '<span class="toast-message">' + escapeHtml(message) + '</span>' +
                       '<button class="toast-close" aria-label="Close">&times;</button>';
      
      container.appendChild(toast);
      
      // Animate in
      requestAnimationFrame(function() {
        toast.classList.add('show');
      });
      
      // Auto remove
      const timeout = setTimeout(function() {
        removeToast(toast);
      }, duration);
      
      // Close button
      toast.querySelector('.toast-close').addEventListener('click', function() {
        clearTimeout(timeout);
        removeToast(toast);
      });
    };
    
    function createToastContainer() {
      const container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
      return container;
    }
    
    function removeToast(toast) {
      toast.classList.remove('show');
      toast.addEventListener('transitionend', function() {
        toast.remove();
      });
    }
  }

  // ========== Modals ==========
  function initModals() {
    document.addEventListener('click', function(e) {
      // Open modal
      const trigger = e.target.closest('[data-modal]');
      if (trigger) {
        e.preventDefault();
        const modalId = trigger.getAttribute('data-modal');
        const modal = document.getElementById(modalId);
        if (modal) openModal(modal);
      }
      
      // Close modal
      if (e.target.matches('.modal-backdrop, [data-dismiss="modal"]')) {
        const modal = e.target.closest('.modal');
        if (modal) closeModal(modal);
      }
    });
    
    // ESC to close
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        const openModal = document.querySelector('.modal.show');
        if (openModal) closeModal(openModal);
      }
    });
    
    window.openModal = function(modal) {
      if (typeof modal === 'string') {
        modal = document.getElementById(modal);
      }
      if (!modal) return;
      
      modal.classList.add('show');
      document.body.classList.add('modal-open');
      modal.setAttribute('aria-hidden', 'false');
      
      const focusable = modal.querySelector('input, button, [tabindex]:not([tabindex="-1"])');
      if (focusable) focusable.focus();
    };
    
    window.closeModal = function(modal) {
      if (typeof modal === 'string') {
        modal = document.getElementById(modal);
      }
      if (!modal) return;
      
      modal.classList.remove('show');
      document.body.classList.remove('modal-open');
      modal.setAttribute('aria-hidden', 'true');
    };
  }

  // ========== Forms ==========
  function initForms() {
    // Saved views (R13): the "save current view" form is rendered outside
    // the HTMX swap zones, so its server-rendered `query` value goes stale
    // after client-side filtering. Sync it with the live URL at submit time
    // (delegated — survives any DOM swaps; the server re-sanitizes anyway).
    document.addEventListener('submit', function(e) {
      const form = e.target.closest ? e.target.closest('form[data-saved-view-save]') : null;
      if (!form) return;
      const queryInput = form.querySelector('input[name="query"]');
      if (queryInput) {
        queryInput.value = window.location.search.replace(/^\?/, '');
      }
    });

    // Form validation feedback
    document.querySelectorAll('form[data-validate]').forEach(function(form) {
      form.addEventListener('submit', function(e) {
        if (!form.checkValidity()) {
          e.preventDefault();
          e.stopPropagation();
        }
        form.classList.add('was-validated');
      });
    });
    
    // Confirm dialogs
    document.addEventListener('click', function(e) {
      const trigger = e.target.closest('[data-confirm]');
      if (trigger) {
        const message = trigger.getAttribute('data-confirm');
        if (!confirm(message)) {
          e.preventDefault();
        }
      }
    });
    
    // AJAX form submissions
    document.querySelectorAll('form[data-ajax]').forEach(function(form) {
      form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const submitBtn = form.querySelector('[type="submit"]');
        const originalText = submitBtn ? submitBtn.textContent : '';
        
        try {
          if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Saving...';
          }
          
          const formData = new FormData(form);
          const response = await fetch(form.action, {
            method: form.method || 'POST',
            body: formData,
            headers: {
              'X-Requested-With': 'XMLHttpRequest'
            }
          });
          
          if (response.ok) {
            const data = await response.json();
            if (data.redirect) {
              window.location.href = data.redirect;
            } else if (data.message) {
              showToast(data.message, 'success');
            }
          } else {
            const error = await response.json();
            showToast(error.message || 'An error occurred', 'error');
          }
        } catch (err) {
          showToast('Network error', 'error');
        } finally {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
          }
        }
      });
    });
  }

  // ========== Keyboard Shortcuts ==========
  function initKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
      // Cmd/Ctrl + K for command palette
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        const palette = document.getElementById('command-palette');
        if (palette) {
          toggleCommandPalette();
        }
      }
      
      // Cmd/Ctrl + S to save current form
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        const activeForm = document.querySelector('form:not([data-no-shortcut])');
        if (activeForm && document.activeElement.closest('form') === activeForm) {
          e.preventDefault();
          activeForm.requestSubmit();
        }
      }
    });
  }

  // ========== Command Palette ==========
  window.toggleCommandPalette = function() {
    const palette = document.getElementById('command-palette');
    if (!palette) return;
    
    if (palette.classList.contains('show')) {
      palette.classList.remove('show');
    } else {
      palette.classList.add('show');
      const input = palette.querySelector('input');
      if (input) {
        input.value = '';
        input.focus();
      }
    }
  };

  // ========== Utilities ==========
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Expose utilities
  window.LexigramAdmin = {
    showToast: function(msg, type, dur) { return window.showToast(msg, type, dur); },
    openModal: function(m) { return window.openModal(m); },
    closeModal: function(m) { return window.closeModal(m); },
    toggleCommandPalette: toggleCommandPalette
  };

})();
