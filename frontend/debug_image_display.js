// 在浏览器控制台运行这个脚本来调试图片显示问题
console.log('🔍 调试多人任务图片显示问题');

// 获取当前任务ID
const taskId = window.location.pathname.split('/tasks/')[1];
console.log('📋 任务ID:', taskId);

// 检查任务数据
fetch(`/api/tasks/${taskId}/`)
  .then(response => response.json())
  .then(data => {
    console.log('📊 任务数据:', data);

    if (data.participants) {
      console.log('👥 参与者数量:', data.participants.length);

      data.participants.forEach((participant, index) => {
        console.log(`\n👤 参与者 ${index + 1}: ${participant.participant.username}`);
        console.log('   提交内容:', participant.submission_text ? '有' : '无');
        console.log('   提交文件数量:', participant.submission_files ? participant.submission_files.length : 0);

        if (participant.submission_files && participant.submission_files.length > 0) {
          participant.submission_files.forEach((file, fileIndex) => {
            console.log(`   📁 文件 ${fileIndex + 1}:`);
            console.log('      文件名:', file.file_name);
            console.log('      URL:', file.file_url);
            console.log('      类型:', file.file_type);
            console.log('      是图片:', file.is_image);
            console.log('      是主要文件:', file.is_primary);

            // 测试图片加载
            const testImg = new Image();
            testImg.onload = function() {
              console.log(`      ✅ 图片加载成功: ${file.file_name} (${this.naturalWidth}x${this.naturalHeight})`);
            };
            testImg.onerror = function() {
              console.log(`      ❌ 图片加载失败: ${file.file_name}`);
            };
            testImg.src = file.file_url;
          });
        }
      });
    }

    // 检查DOM中的参与者文件元素
    setTimeout(() => {
      console.log('\n🎨 检查DOM元素:');

      const participantCards = document.querySelectorAll('.participant-card');
      console.log('参与者卡片数量:', participantCards.length);

      participantCards.forEach((card, index) => {
        const username = card.querySelector('.participant-name')?.textContent;
        const filesSection = card.querySelector('.participant-files');
        const images = card.querySelectorAll('.preview-image');

        console.log(`\n卡片 ${index + 1} (${username}):`);
        console.log('  有文件区域:', !!filesSection);
        console.log('  图片元素数量:', images.length);

        images.forEach((img, imgIndex) => {
          console.log(`  图片 ${imgIndex + 1}:`);
          console.log('    src:', img.src);
          console.log('    alt:', img.alt);
          console.log('    完成加载:', img.complete);
          console.log('    自然宽度:', img.naturalWidth);
          console.log('    自然高度:', img.naturalHeight);
          console.log('    显示样式:', window.getComputedStyle(img).display);
          console.log('    可见性:', window.getComputedStyle(img).visibility);
          console.log('    不透明度:', window.getComputedStyle(img).opacity);

          if (img.naturalWidth === 0) {
            console.log('    ⚠️ 图片可能加载失败');
          }
        });
      });
    }, 2000);
  })
  .catch(error => {
    console.error('❌ 获取任务数据失败:', error);
  });

// 监听图片加载错误
document.addEventListener('error', function(e) {
  if (e.target.tagName === 'IMG') {
    console.error('🖼️ 图片加载错误:', e.target.src);
  }
}, true);

console.log('✅ 调试脚本已启动，请等待结果...');