// 在浏览器控制台运行这个脚本来调试提交文件显示
console.log('🔍 调试提交文件显示');

// 检查当前页面的任务数据
if (window.location.pathname.includes('/tasks/')) {
  const taskId = window.location.pathname.split('/tasks/')[1];
  console.log('📋 当前任务ID:', taskId);

  // 检查Vue应用实例
  const app = document.querySelector('#app').__vue_app__;
  if (app) {
    console.log('✅ 找到Vue应用实例');

    // 获取任务数据
    fetch(`/api/tasks/${taskId}/`)
      .then(response => response.json())
      .then(data => {
        console.log('📊 任务数据:', data);

        if (data.participants) {
          console.log('👥 参与者数量:', data.participants.length);

          data.participants.forEach((participant, index) => {
            console.log(`👤 参与者 ${index + 1}:`, participant.participant.username);
            console.log('   提交内容:', participant.submission_text ? '有' : '无');
            console.log('   提交文件:', participant.submission_files ? participant.submission_files.length : 0, '个');

            if (participant.submission_files && participant.submission_files.length > 0) {
              participant.submission_files.forEach((file, fileIndex) => {
                console.log(`   📁 文件 ${fileIndex + 1}:`, file.file_name);
                console.log('      URL:', file.file_url);
                console.log('      类型:', file.file_type);
                console.log('      是图片:', file.is_image);
                console.log('      是主要文件:', file.is_primary);
              });
            }
          });
        }

        // 检查DOM中的参与者文件元素
        const participantFiles = document.querySelectorAll('.participant-files');
        console.log('🎨 DOM中的参与者文件元素:', participantFiles.length, '个');

        participantFiles.forEach((element, index) => {
          console.log(`   元素 ${index + 1}:`, element);
          const images = element.querySelectorAll('.preview-image');
          console.log('     图片元素:', images.length, '个');

          images.forEach((img, imgIndex) => {
            console.log(`     图片 ${imgIndex + 1}:`, img.src);
            console.log('       是否加载:', img.complete);
            console.log('       自然宽度:', img.naturalWidth);
            console.log('       自然高度:', img.naturalHeight);
          });
        });
      })
      .catch(error => {
        console.error('❌ 获取任务数据失败:', error);
      });
  } else {
    console.log('❌ 未找到Vue应用实例');
  }
} else {
  console.log('❌ 不在任务详情页面');
}

// 检查网络请求
console.log('🌐 检查网络请求...');
const observer = new PerformanceObserver((list) => {
  list.getEntries().forEach((entry) => {
    if (entry.name.includes('tasks') || entry.name.includes('submission')) {
      console.log('📡 网络请求:', entry.name, '状态:', entry.responseStatus || 'Unknown');
    }
  });
});
observer.observe({entryTypes: ['navigation', 'resource']});

console.log('✅ 调试脚本已运行，请检查上述输出');
console.log('💡 如果看不到图片，请检查:');
console.log('   1. 参与者是否有 submission_files 数据');
console.log('   2. 图片URL是否正确');
console.log('   3. 图片是否成功加载');
console.log('   4. CSS样式是否正确应用');