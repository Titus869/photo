document.addEventListener('DOMContentLoaded', () => {

  // 检查是否登录（检查 localStorage 中是否有 username）
  const username = localStorage.getItem('username');
  if (!username) {
    alert('您尚未登录，请先登录');
    window.location.href = 'index.html'; // 跳转登录页
    return;
  }

  // 获取 DOM 元素
  const userDisplayBtn = document.getElementById('user-display-btn');
  const logoutBtnDropdown = document.getElementById('logout-btn-dropdown');

  const categoriesList = document.querySelector('.categories-list');
  const searchCategoryInput = document.getElementById('search-category-input');
  const searchCategoryBtn = document.getElementById('search-category-btn');
  const resetCategorySearchBtn = document.getElementById('reset-category-btn');
  const newCategoryInput = document.getElementById('new-category-input');
  const addCategoryBtn = document.getElementById('add-category-btn');
  const deleteCategorySelect = document.getElementById('deleteCategorySelect');
  const deleteCategoryBtn = document.getElementById('deleteCategoryBtn');

  const categorySelect = document.getElementById('category-select');
  const imageUpload = document.getElementById('image-upload');
  const uploadBtn = document.getElementById('upload-btn');
  const fileNameDisplay = document.getElementById('file-name-display'); // 用于显示文件名称

  const imageGallery = document.getElementById('image-gallery');
  const searchImageInput = document.getElementById('search-image-input');
  const searchImageBtn = document.getElementById('search-image-btn');
  const resetImageSearchBtn = document.getElementById('reset-image-btn');
  const currentCategoryDisplay = document.getElementById('current-category-display');

  // 编辑面板元素
  const editPanel = document.getElementById('edit-panel');
  const editImage = document.getElementById('edit-image');
  const editFilenameInput = document.getElementById('edit-filename');
  const editCommentInput = document.getElementById('edit-comment');
  const saveChangesBtn = document.getElementById('save-changes-btn');
  const deleteImageBtn = document.getElementById('delete-image-btn');
  const closeEditorBtn = document.getElementById('close-editor-btn');

  // 分类和图片的数据结构
  // categories = { "分类名称": [ { url, filename, comment, filepath }, ... ] }
  const categories = {};

  // 当前正在编辑的图片: { category, index }
  let currentEdit = null;
  // 跟踪当前正在查看的分类，用于图片搜索
  let currentActiveCategory = '';

  // 显示当前用户名
  userDisplayBtn.textContent = username;

  // 登出按钮事件（来自下拉菜单）
  logoutBtnDropdown.addEventListener('click', () => {
    localStorage.clear(); // 清除本地存储中的用户名

    // 调用后端登出 API
    fetch('http://127.0.0.1:5000/logout', {
      method: 'POST',
      credentials: 'include' // 包含 cookie
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          alert('已登出，跳转登录页面');
          window.location.href = 'index.html'; // 重定向到登录页面
        } else {
          alert('登出失败，请重试');
        }
      })
      .catch(() => alert('网络错误，请稍后再试'));
  });

  // 分类管理功能和事件监听器

  // 刷新分类（按钮和下拉菜单）
  function refreshCategories(searchTerm = '') {
    fetch('http://127.0.0.1:5000/categories', {
      credentials: 'include' // 包含 cookie
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          const allCategoryList = data.categories;
          let categoryListToDisplay = allCategoryList;

          if (searchTerm) {
            const lowerCaseSearchTerm = searchTerm.toLowerCase();
            categoryListToDisplay = allCategoryList.filter(cat =>
              cat.toLowerCase().includes(lowerCaseSearchTerm)
            );
          }

          // 清空 UI 元素
          categoriesList.innerHTML = '';
          categorySelect.innerHTML = '<option value="" disabled selected>选择分类</option>';
          deleteCategorySelect.innerHTML = '<option value="" disabled selected>选择要删除的分类</option>';

          // 更新前端 categories 对象（仍然使用所有分类）
          allCategoryList.forEach(cat => {
            if (!categories[cat]) {
              categories[cat] = [];
            }
          });

          // 渲染要显示的分类按钮
          categoryListToDisplay.forEach(cat => {
            const btn = document.createElement('button');
            btn.textContent = cat;
            btn.addEventListener('click', () => {
              showImages(cat);
            });
            categoriesList.appendChild(btn);
          });

          // 填充下拉菜单（这些应该始终显示所有分类）
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

  // 添加新分类
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
      credentials: 'include', // 包含 cookie
      body: JSON.stringify({ category: newCat })
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          categories[newCat] = []; // 更新前端缓存
          newCategoryInput.value = '';
          refreshCategories();
        } else {
          alert(data.message || '添加失败');
        }
      })
      .catch(() => alert('网络错误，请稍后再试'));
  });

  // 删除分类
  deleteCategoryBtn.addEventListener('click', () => {
    const selectedDeleteCat = deleteCategorySelect.value;
    if (!selectedDeleteCat) {
      alert('请选择要删除的分类');
      return;
    }
    if (confirm(`确定删除分类 "${selectedDeleteCat}" 及其所有图片吗？`)) {
      fetch('http://127.0.0.1:5000/delete_category', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include', // 包含 cookie
        body: JSON.stringify({ category: selectedDeleteCat })
      })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            // alert('分类已删除');
            refreshCategories(); // 删除后刷新分类
            // imageGallery.innerHTML = ''; // 清空图片显示
            closeEditPanel(); // 关闭编辑面板
          } else {
            alert(data.message || '删除失败，请稍后重试');
          }
        })
        .catch(() => alert('网络错误，请稍后再试'));
    }
  });

  // 搜索分类按钮事件
  searchCategoryBtn.addEventListener('click', () => {
    const searchTerm = searchCategoryInput.value.trim();
    refreshCategories(searchTerm);
  });

  // 重置分类搜索按钮事件
  resetCategorySearchBtn.addEventListener('click', () => {
    searchCategoryInput.value = '';
    refreshCategories();
  });

  // 上传图片部分功能和事件监听器

  // 显示选定的文件名称
  imageUpload.addEventListener('change', () => {
    if (imageUpload.files.length > 0) {
      fileNameDisplay.textContent = imageUpload.files[0].name;
    } else {
      fileNameDisplay.textContent = '未选择文件';
    }
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
      credentials: 'include', // 包含 cookie
      body: formData
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          closeEditPanel();
          // alert('图片上传成功');
          // 刷新当前选定分类的图片
          showImages(selectedCategory);
          imageUpload.value = ''; // 清空文件输入框
          fileNameDisplay.textContent = '未选择文件'; // 重置文件名称显示
        } else {
          alert(data.message || '上传失败');
        }
      })
      .catch(() => alert('网络错误，请稍后再试'));
  });

  // 图片画廊功能和事件监听器

  // 显示特定分类的图片
  async function showImages(category, imageSearchTerm = '') {
    if (!category) return;

    currentActiveCategory = category; // 更新当前活跃的分类

    currentCategoryDisplay.textContent = ` (${category})`; // 显示当前分类
    if (!category) { // 如果没有选择分类，清除显示
      currentCategoryDisplay.textContent = '';
    }

    imageGallery.innerHTML = ''; // 清空画廊
    closeEditPanel(); // 关闭编辑面板

    try {
      const res = await fetch(`http://127.0.0.1:5000/get_images?category=${encodeURIComponent(category)}`, {
        credentials: 'include' // 包含 cookie
      });

      const data = await res.json();
      if (!data.success) {
        alert(data.message || '获取图片失败');
        return;
      }

      categories[category] = data.images || []; // 更新前端缓存

      let imagesToDisplay = categories[category];

      if (imageSearchTerm) {
        const lowerCaseImageSearchTerm = imageSearchTerm.toLowerCase();
        imagesToDisplay = imagesToDisplay.filter(imgObj =>
          imgObj.filename.toLowerCase().includes(lowerCaseImageSearchTerm) ||
          (imgObj.comment && imgObj.comment.toLowerCase().includes(lowerCaseImageSearchTerm))
        );
      }

      // 渲染图片
      if (imagesToDisplay.length === 0) {
        imageGallery.innerHTML = '<p style="text-align: center; color: #555;">暂无图片或未找到匹配图片。</p>';
      } else {
        imagesToDisplay.forEach((imgObj) => {
          const imageItemWrapper = document.createElement('div');
          imageItemWrapper.className = 'image-item-wrapper';

          const img = document.createElement('img');
          img.src = `http://127.0.0.1:5000${imgObj.url}`;
          img.alt = imgObj.filename;
          imageItemWrapper.appendChild(img);

          const p = document.createElement('p');
          p.textContent = imgObj.filename;
          imageItemWrapper.appendChild(p);

          const tooltipSpan = document.createElement('span');
          tooltipSpan.className = 'tooltiptext';
          tooltipSpan.textContent = imgObj.filename;
          imageItemWrapper.appendChild(tooltipSpan);

          imageItemWrapper.addEventListener('click', () => {
            // 找到图片在原始分类数组中的索引
            const originalIndex = categories[category].findIndex(item => item.filepath === imgObj.filepath);
            if (originalIndex !== -1) {
              openEditPanel(category, originalIndex);
            } else {
              console.error('错误：无法找到图片的原始索引:', imgObj.filepath);
            }
          });

          imageGallery.appendChild(imageItemWrapper);
        });
      }

    } catch (err) {
      console.error('加载图片失败:', err);
      alert('网络错误，请稍后再试');
    }
  }

  // 图片搜索按钮事件
  searchImageBtn.addEventListener('click', () => {
    const searchTerm = searchImageInput.value.trim();
    if (currentActiveCategory) {
      showImages(currentActiveCategory, searchTerm);
      closeEditPanel();
    } else {
      alert('请先选择一个分类，再进行图片搜索。');
    }
  });

  // 重置图片搜索按钮事件
  resetImageSearchBtn.addEventListener('click', () => {
    searchImageInput.value = '';
    if (currentActiveCategory) {
      showImages(currentActiveCategory); // 重新加载当前分类的所有图片
      closeEditPanel();
    } else {
      alert('请先选择一个分类。');
      currentCategoryDisplay.textContent = ''; // 如果没有活跃分类，确保清空显示
    }
  });

  // 编辑面板功能和事件监听器

  // 打开编辑面板
  function openEditPanel(category, index) {
    const imgObj = categories[category][index];
    currentEdit = { category, index };

    editImage.src = `http://127.0.0.1:5000${imgObj.url}`;
    editFilenameInput.value = imgObj.filename;
    editCommentInput.value = imgObj.comment || ''; // 如果没有备注则显示空字符串

    editPanel.style.display = 'block';
  }

  // 保存图片更改
  saveChangesBtn.addEventListener('click', () => {
    if (!currentEdit) return; // 如果没有当前编辑的图片，则返回

    const { category, index } = currentEdit;
    const imgObj = categories[category][index];
    const newFilename = editFilenameInput.value.trim() || imgObj.filename; // 如果新文件名为空，则使用原文件名
    const newComment = editCommentInput.value.trim();

    fetch('http://127.0.0.1:5000/update_image', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include', // 包含 cookie
      body: JSON.stringify({
        filepath: imgObj.url.replace('/uploads/', ''), // 发送相对路径
        filename: newFilename,
        comment: newComment
      })
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          // alert('修改成功');
          // 更新前端缓存
          categories[category][index].filename = newFilename;
          categories[category][index].comment = newComment;
          closeEditPanel();
          showImages(currentActiveCategory); // 刷新当前分类的图片显示
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
      fetch('http://127.0.0.1:5000/delete_image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include', // 包含 cookie
        body: JSON.stringify({
          filepath: imgObj.url.replace('/uploads/', '') // 发送相对路径
        })
      })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            // alert('图片已删除');
            // 更新前端缓存
            categories[category].splice(index, 1);
            closeEditPanel();
            showImages(currentActiveCategory); // 刷新当前分类的图片显示
          } else {
            alert(data.message || '删除失败');
          }
        })
        .catch(() => alert('网络错误，请稍后再试'));
    }
  });

  // 关闭编辑面板
  closeEditorBtn.addEventListener('click', closeEditPanel);
  function closeEditPanel() {
    editPanel.style.display = 'none';
    currentEdit = null;
  }

  // 初始化页面
  refreshCategories();
});