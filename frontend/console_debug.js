// 在浏览器控制台运行这个脚本来调试Vue组件中的图片显示问题
console.log('🔍 开始Vue组件图片显示调试');

// 获取当前任务ID
const taskId = window.location.pathname.split('/tasks/')[1];
console.log('📋 任务ID:', taskId);

// 检查Vue应用实例
if (window.__VUE_DEVTOOLS_GLOBAL_HOOK__) {
    console.log('✅ Vue DevTools 可用');
} else {
    console.log('⚠️ Vue DevTools 不可用');
}

// 检查DOM中的参与者数据
setTimeout(() => {
    console.log('\n🎨 检查DOM结构:');

    // 查找参与者卡片
    const participantCards = document.querySelectorAll('.participant-card');
    console.log(`找到 ${participantCards.length} 个参与者卡片`);

    participantCards.forEach((card, index) => {
        const username = card.querySelector('.participant-name')?.textContent?.trim();
        const filesSection = card.querySelector('.participant-files');
        const filesGrid = card.querySelector('.files-grid');
        const fileItems = card.querySelectorAll('.file-item');
        const images = card.querySelectorAll('.preview-image');

        console.log(`\n👤 参与者卡片 ${index + 1}:`);
        console.log(`  用户名: ${username}`);
        console.log(`  有文件区域: ${!!filesSection}`);
        console.log(`  有文件网格: ${!!filesGrid}`);
        console.log(`  文件项数量: ${fileItems.length}`);
        console.log(`  图片元素数量: ${images.length}`);

        // 检查每个文件项
        fileItems.forEach((item, itemIndex) => {
            const isImageFile = item.classList.contains('image-file');
            const filePreview = item.querySelector('.file-preview');
            const img = item.querySelector('.preview-image');

            console.log(`  文件项 ${itemIndex + 1}:`);
            console.log(`    是图片文件: ${isImageFile}`);
            console.log(`    有预览容器: ${!!filePreview}`);
            console.log(`    有图片元素: ${!!img}`);

            if (img) {
                console.log(`    图片src: ${img.src}`);
                console.log(`    图片alt: ${img.alt}`);
                console.log(`    加载完成: ${img.complete}`);
                console.log(`    自然宽度: ${img.naturalWidth}`);
                console.log(`    自然高度: ${img.naturalHeight}`);
                console.log(`    显示样式: ${window.getComputedStyle(img).display}`);
                console.log(`    可见性: ${window.getComputedStyle(img).visibility}`);
                console.log(`    不透明度: ${window.getComputedStyle(img).opacity}`);

                if (img.naturalWidth === 0) {
                    console.log(`    ⚠️ 图片可能加载失败或正在加载中`);
                }
            }
        });
    });

    // 检查API数据
    console.log('\n📡 检查API数据:');
    fetch(`/api/tasks/${taskId}/`)
        .then(response => response.json())
        .then(data => {
            console.log('API响应数据:', data);

            if (data.participants) {
                console.log(`API返回 ${data.participants.length} 个参与者`);

                data.participants.forEach((participant, index) => {
                    console.log(`\n参与者 ${index + 1}: ${participant.participant.username}`);
                    console.log(`  提交文件: ${participant.submission_files?.length || 0} 个`);

                    if (participant.submission_files) {
                        participant.submission_files.forEach((file, fileIndex) => {
                            console.log(`  文件 ${fileIndex + 1}:`);
                            console.log(`    ID: ${file.id}`);
                            console.log(`    URL: ${file.file_url}`);
                            console.log(`    类型: ${file.file_type}`);
                            console.log(`    是图片: ${file.is_image}`);

                            // 测试直接访问图片
                            const testImg = new Image();
                            testImg.onload = function() {
                                console.log(`    ✅ 图片直接访问成功: ${file.file_url} (${this.naturalWidth}x${this.naturalHeight})`);
                            };
                            testImg.onerror = function() {
                                console.log(`    ❌ 图片直接访问失败: ${file.file_url}`);
                            };
                            testImg.src = file.file_url;
                        });
                    }
                });
            }
        })
        .catch(error => {
            console.error('❌ API请求失败:', error);
        });

}, 2000);

// 监听图片加载错误
document.addEventListener('error', function(e) {
    if (e.target.tagName === 'IMG') {
        console.error('🖼️ 图片加载错误事件:', {
            src: e.target.src,
            alt: e.target.alt,
            className: e.target.className
        });
    }
}, true);

// 监听图片加载成功
document.addEventListener('load', function(e) {
    if (e.target.tagName === 'IMG') {
        console.log('🖼️ 图片加载成功事件:', {
            src: e.target.src,
            alt: e.target.alt,
            className: e.target.className,
            naturalWidth: e.target.naturalWidth,
            naturalHeight: e.target.naturalHeight
        });
    }
}, true);

console.log('✅ 调试脚本已启动，请等待2秒后查看结果...');