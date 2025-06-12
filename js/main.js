document.addEventListener('DOMContentLoaded', () => {

  // 检查是否登录（检查 localStorage 中是否有 username）
  const username = localStorage.getItem('username');
  if (!username) {
    alert('您尚未登录，请先登录');
    window.location.href = 'index.html'; // 跳转登录页
    return;
  }

  const categoriesList = document.querySelector('.categories-list');
  const newCategoryInput = document.getElementById('new-category-input');
  const addCategoryBtn = document.getElementById('add-category-btn');
  const categorySelect = document.getElementById('category-select');
  const imageUpload = document.getElementById('image-upload');
  const uploadBtn = document.getElementById('upload-btn');
  const imageGallery = document.getElementById('image-gallery');
  const deleteCategorySelect = document.getElementById('deleteCategorySelect');
  const deleteCategoryBtn = document.getElementById('deleteCategoryBtn');

  // 编辑面板元素
  const editPanel = document.getElementById('edit-panel');
  const editImage = document.getElementById('edit-image');
  const editFilenameInput = document.getElementById('edit-filename');
  const editCommentInput = document.getElementById('edit-comment');
  const saveChangesBtn = document.getElementById('save-changes-btn');
  const deleteImageBtn = document.getElementById('delete-image-btn');
  const closeEditorBtn = document.getElementById('close-editor-btn');

  const searchCategoryInput = document.getElementById('search-category-input');
  const searchCategoryBtn = document.getElementById('search-category-btn');
  const resetCategorySearchBtn = document.getElementById('reset-category-btn');


  // 分类及图片数据结构
  // categories = { "分类名": [ { url, filename, comment }, ... ] }
  const categories = {};

  // 当前编辑图片的状态：{ category, index }
  let currentEdit = null;

  // 新增的元素
  const userDisplayBtn = document.getElementById('user-display-btn');
  const logoutBtnDropdown = document.getElementById('logout-btn-dropdown');
  const friendsListBtn = document.getElementById('friends-list-btn');
  const userMenuContainer = document.querySelector('.user-menu-container');
  const dropdownMenu = document.querySelector('.dropdown-menu');

  // 显示当前用户名
  userDisplayBtn.textContent = username;

  // 登出按钮事件 (来自下拉菜单)
  logoutBtnDropdown.addEventListener('click', () => {
    localStorage.clear(); // 清除本地存储的用户名

    // 调用后端登出接口
    fetch('http://127.0.0.1:5000/logout', {
      method: 'POST',
      credentials: 'include'
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          alert('已登出，跳转登录页面');
          window.location.href = 'index.html';  // 跳转登录页
        } else {
          alert('登出失败，请重试');
        }
      })
      .catch(() => alert('网络错误，请稍后再试'));
  });

  // 好友列表按钮事件 (这里只是一个占位符)
  friendsListBtn.addEventListener('click', (e) => {
    e.preventDefault(); // 阻止默认的链接跳转
    alert('好友列表功能待开发！');
    // 你可以在这里添加跳转到好友列表页面的逻辑
  });

  // 更新分类按钮和下拉菜单
// 更新分类按钮和下拉菜单
  function refreshCategories(searchTerm = '') { // <-- 修改这里，添加 searchTerm 参数
    fetch('http://127.0.0.1:5000/categories', {
      credentials: 'include'
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          const allCategoryList = data.categories; // 获取所有分类
          let categoryListToDisplay = allCategoryList; // 默认显示所有

          // 如果有搜索词，则进行筛选
          if (searchTerm) {
            const lowerCaseSearchTerm = searchTerm.toLowerCase();
            categoryListToDisplay = allCategoryList.filter(cat =>
              cat.toLowerCase().includes(lowerCaseSearchTerm)
            );
          }

          // 清空界面元素
          categoriesList.innerHTML = '';
          categorySelect.innerHTML = '<option value="" disabled selected>选择分类</option>';
          deleteCategorySelect.innerHTML = '<option value="" disabled selected>选择要删除的分类</option>';

          // 更新前端 categories 对象 (这里仍使用所有分类，因为categories对象是缓存所有数据的)
          allCategoryList.forEach(cat => { // 注意这里仍然遍历 allCategoryList
            if (!categories[cat]) {
              categories[cat] = [];
            }
          });

          // 渲染要显示的分类按钮
          categoryListToDisplay.forEach(cat => { // <-- 这里改为遍历 categoryListToDisplay
            // 分类按钮
            const btn = document.createElement('button');
            btn.textContent = cat;
            btn.addEventListener('click', () => {
              showImages(cat);
            });
            categoriesList.appendChild(btn);
          });

          // 填充上传图片和删除分类的下拉菜单（这些应该总是显示所有分类）
          allCategoryList.forEach(cat => {
            const option1 = document.createElement('option');
            option1.value = cat;
            option1.textContent = cat;
            categorySelect.appendChild(option1);

            const option2 = document.createElement('option');
            option2.value = cat;
            option2.textContent = cat;
            deleteCategorySelect.appendChild(option2);
          });

        } else {
          alert(data.message || '获取分类失败');
        }
      })
      .catch(() => alert('网络错误，请稍后再试'));
  }


  // 删除分类按钮事件
  deleteCategoryBtn.addEventListener('click', () => {
    const selectedDeleteCat = deleteCategorySelect.value;
    if (!selectedDeleteCat) {
      alert('请选择要删除的分类');
      return;
    }
    if (confirm(`确定删除分类 "${selectedDeleteCat}" 及其所有图片吗？`)) {
      // 调用后端接口删除
      fetch('http://127.0.0.1:5000/delete_category', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({ category: selectedDeleteCat })
      })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            alert('分类已删除');
            // refreshCategories();
            imageGallery.innerHTML = ''; // 清空图片展示
            closeEditPanel(); // 如果正在编辑也关闭编辑面板
          } else {
            alert(data.message || '删除失败，请稍后重试');
          }
        })
        .catch(() => alert('网络错误，请稍后再试'));
    }
  });


  // 展示某分类的图片
  // 异步获取并展示某分类的图片
async function showImages(category) {
  if (!category) return;
  imageGallery.innerHTML = '';

  try {
    const res = await fetch(`http://127.0.0.1:5000/get_images?category=${encodeURIComponent(category)}`, {
      credentials: 'include'
    });
    const data = await res.json();
    if (!data.success) {
      alert(data.message || '获取图片失败');
      return;
    }

    // 把从后端拿到的图片列表更新到本地 categories
    categories[category] = data.images || [];

    // 渲染图片
    categories[category].forEach((imgObj, index) => {
      const div = document.createElement('div');
      div.className = 'image-item';
      div.style.cursor = 'pointer';
      div.style.display = 'inline-block';
      div.style.margin = '10px';
      div.style.textAlign = 'center';

      const img = document.createElement('img');
      img.src = imgObj.url;
      img.alt = imgObj.filename;
      img.style.width = '150px';
      img.style.height = '150px';
      img.style.objectFit = 'cover';
      div.appendChild(img);

      const p = document.createElement('p');
      p.textContent = imgObj.filename;
      p.title = imgObj.filename; // 新增：为p标签添加title属性，显示完整文件名
      div.appendChild(p);

      div.addEventListener('click', () => {
        openEditPanel(category, index);
      });

      imageGallery.appendChild(div);
    });
  } catch (err) {
    alert('网络错误，请稍后再试');
  }
}


  // 打开编辑界面
  function openEditPanel(category, index) {
    const imgObj = categories[category][index];
    currentEdit = { category, index };

    editImage.src = imgObj.url;
    editFilenameInput.value = imgObj.filename;
    editCommentInput.value = imgObj.comment || '';

    editPanel.style.display = 'block';
  }

// 保存编辑修改
saveChangesBtn.addEventListener('click', () => {
  if (!currentEdit) return;

  const { category, index } = currentEdit;
  const imgObj = categories[category][index];
  const newFilename = editFilenameInput.value.trim() || imgObj.filename;
  const newComment = editCommentInput.value.trim();

  // 调用后端接口更新
  fetch('http://127.0.0.1:5000/update_image', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({
      filepath: imgObj.url.replace('/uploads/', ''), // 只要相对路径
      filename: newFilename,
      comment: newComment
    })
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        alert('修改成功');
        // 更新前端缓存
        categories[category][index].filename = newFilename;
        categories[category][index].comment = newComment;
        // showImages(category);
        closeEditPanel();
      } else {
        alert(data.message || '修改失败');
      }
    })
    .catch(() => alert('网络错误，请稍后再试'));
});

// 删除图片
deleteImageBtn.addEventListener('click', () => {
  if (!currentEdit) return;

  const { category, index } = currentEdit;
  const imgObj = categories[category][index];

  if (confirm('确定删除这张图片吗？')) {
    // 调用后端接口删除
    fetch('http://127.0.0.1:5000/delete_image', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        filepath: imgObj.url.replace('/uploads/', '') // 只要相对路径
      })
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          alert('图片已删除');
          // 更新前端缓存
          categories[category].splice(index, 1);
          // showImages(category);
          closeEditPanel();
        } else {
          alert(data.message || '删除失败');
        }
      })
      .catch(() => alert('网络错误，请稍后再试'));
  }
});


  // 关闭编辑界面
  closeEditorBtn.addEventListener('click', closeEditPanel);
  function closeEditPanel() {
    editPanel.style.display = 'none';
    currentEdit = null;
  }

  // 新增分类
  addCategoryBtn.addEventListener('click', () => {
    const newCat = newCategoryInput.value.trim();
    if (!newCat) {
      alert('请输入分类名称');
      return;
    }

    fetch('http://127.0.0.1:5000/add_category', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      credentials: 'include',
      body: JSON.stringify({ category: newCat })
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          // alert('分类添加成功');
          // 更新前端本地 categories 对象
          categories[newCat] = [];
          newCategoryInput.value = '';
          refreshCategories();
        } else {
          alert(data.message || '添加失败');
        }
      })
      .catch(() => alert('网络错误，请稍后再试'));
  });

  // 上传图片
  uploadBtn.addEventListener('click', () => {
    const selectedCategory = categorySelect.value;
    if (!selectedCategory) {
      alert('请选择分类');
      return;
    }
    const file = imageUpload.files[0];
    if (!file) {
      alert('请选择图片文件');
      return;
    }

    const formData = new FormData();
    formData.append('category', selectedCategory);
    formData.append('image', file);

    fetch('http://127.0.0.1:5000/upload_image', {
      method: 'POST',
      credentials: 'include',
      body: formData
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          alert('图片上传成功');
          // 上传成功后重新从数据库获取该分类的图片列表
          // showImages(selectedCategory);
          // imageUpload.value = ''; // 清空文件选择框
        } else {
          alert(data.message || '上传失败');
        }
      })
      .catch(() => alert('网络错误，请稍后再试'));
  });

  // 搜索分类按钮事件
  searchCategoryBtn.addEventListener('click', () => {
    const searchTerm = searchCategoryInput.value.trim();
    refreshCategories(searchTerm); // 调用 refreshCategories 并传入搜索词
  });

  // 重置搜索按钮事件
  resetCategorySearchBtn.addEventListener('click', () => {
    searchCategoryInput.value = ''; // 清空搜索输入框
    refreshCategories(); // 不传入搜索词，显示所有分类
  });

  // 初始化
  refreshCategories();
});