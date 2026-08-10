document.addEventListener('DOMContentLoaded', () => {
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      const usernameInput = document.getElementById('username').value;
      const passwordInput = document.getElementById('password').value;
      const errorMsg = document.getElementById('error-msg');
      const loginBtn = document.getElementById('login-btn');
      
      errorMsg.style.display = 'none';
      loginBtn.disabled = true;
      loginBtn.innerText = 'جاري التحقق...';
      
      try {
        const formData = new URLSearchParams();
        formData.append('username', usernameInput);
        formData.append('password', passwordInput);
        
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          body: formData
        });
        
        if (res.ok) {
          const data = await res.json();
          localStorage.setItem('cm_token', data.access_token);
          window.location.href = '/';
        } else {
          errorMsg.innerText = 'اسم المستخدم أو كلمة المرور غير صحيحة';
          errorMsg.style.display = 'block';
        }
      } catch (err) {
        errorMsg.innerText = 'حدث خطأ في الاتصال بالخادم';
        errorMsg.style.display = 'block';
      } finally {
        loginBtn.disabled = false;
        loginBtn.innerText = 'دخول';
      }
    });
  }
});

// Helper function to append token to fetch requests
function getAuthHeaders() {
  const token = localStorage.getItem('cm_token');
  if (!token) {
    window.location.href = '/login.html';
    return {};
  }
  return {
    'Authorization': `Bearer ${token}`
  };
}

function logout() {
  localStorage.removeItem('cm_token');
  window.location.href = '/login.html';
}

// Global fetch interceptor to attach JWT token to all API requests
const originalFetch = window.fetch;
window.fetch = async function() {
  let [resource, config] = arguments;
  
  // Only intercept API calls, exclude login itself
  if (typeof resource === 'string' && resource.includes('/api/') && !resource.includes('/api/auth/login')) {
    config = config || {};
    config.headers = config.headers || {};
    
    const token = localStorage.getItem('cm_token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
  }
  
  const response = await originalFetch(resource, config);
  
  // If unauthorized, redirect to login
  if (response.status === 401 && window.location.pathname !== '/login.html') {
    localStorage.removeItem('cm_token');
    window.location.href = '/login.html';
  }
  
  return response;
};

// Global token check on protected pages for initial load
if (window.location.pathname !== '/login.html' && window.location.pathname !== '/login') {
  if (!localStorage.getItem('cm_token')) {
    window.location.href = '/login.html';
  }
}
