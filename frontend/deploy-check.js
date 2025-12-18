#!/usr/bin/env node

/**
 * 部署检查脚本
 * 检查构建文件和部署状态
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

console.log('🔍 检查前端构建和部署状态');
console.log('=' * 60);

// 检查构建目录
const distPath = path.join(__dirname, 'dist');
const indexPath = path.join(distPath, 'index.html');
const assetsPath = path.join(distPath, 'assets');

console.log('📁 检查构建文件:');

if (!fs.existsSync(distPath)) {
  console.log('❌ dist 目录不存在，请先运行 npm run build');
  process.exit(1);
}

if (!fs.existsSync(indexPath)) {
  console.log('❌ index.html 不存在');
  process.exit(1);
}

if (!fs.existsSync(assetsPath)) {
  console.log('❌ assets 目录不存在');
  process.exit(1);
}

// 读取 index.html 内容
const indexContent = fs.readFileSync(indexPath, 'utf8');
console.log('✅ index.html 存在');

// 提取资源文件引用
const jsMatches = indexContent.match(/src="\/assets\/(.*?)"/g);
const cssMatches = indexContent.match(/href="\/assets\/(.*?)"/g);

console.log('\n📋 HTML 中引用的资源:');

if (jsMatches) {
  jsMatches.forEach(match => {
    const filename = match.match(/assets\/(.*?)"/)[1];
    const filePath = path.join(assetsPath, filename);
    const exists = fs.existsSync(filePath);
    console.log(`${exists ? '✅' : '❌'} JS: ${filename} ${exists ? '(存在)' : '(不存在)'}`);
  });
}

if (cssMatches) {
  cssMatches.forEach(match => {
    const filename = match.match(/assets\/(.*?)"/)[1];
    const filePath = path.join(assetsPath, filename);
    const exists = fs.existsSync(filePath);
    console.log(`${exists ? '✅' : '❌'} CSS: ${filename} ${exists ? '(存在)' : '(不存在)'}`);
  });
}

// 列出实际的 assets 文件
console.log('\n📂 实际的 assets 文件:');
const assetFiles = fs.readdirSync(assetsPath);
assetFiles.forEach(file => {
  const stats = fs.statSync(path.join(assetsPath, file));
  console.log(`📄 ${file} (${(stats.size / 1024).toFixed(2)} KB)`);
});

console.log('\n💡 部署建议:');
console.log('1. 确保所有文件都已上传到服务器');
console.log('2. 清除浏览器和CDN缓存');
console.log('3. 检查服务器静态文件配置');
console.log('4. 确认域名和路径配置正确');

console.log('\n🌐 测试URL:');
console.log('- 本地预览: http://localhost:4173/');
console.log('- 生产环境: https://lock-up.zheermao.top/');

// 创建一个简单的文件清单
const manifest = {
  buildTime: new Date().toISOString(),
  files: {
    html: 'index.html',
    assets: assetFiles
  },
  references: {
    js: jsMatches || [],
    css: cssMatches || []
  }
};

fs.writeFileSync(path.join(distPath, 'build-manifest.json'), JSON.stringify(manifest, null, 2));
console.log('\n📝 已生成 build-manifest.json 文件');