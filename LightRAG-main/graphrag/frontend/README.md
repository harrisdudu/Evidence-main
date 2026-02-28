# GraphRAG Frontend

基于 LightRAG WebUI 迁移的 GraphRAG 前端项目。

## 技术栈

- **React 19** - UI框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **Tailwind CSS** - 样式框架
- **Zustand** - 状态管理
- **Sigma.js** - 图谱可视化
- **Radix UI** - 基础组件库

## 项目结构

```
graphrag/frontend/
├── src/
│   ├── api/                    # API层
│   │   ├── types.ts           # 类型定义
│   │   └── client.ts          # API客户端
│   ├── components/
│   │   ├── ui/                # UI基础组件
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── input.tsx
│   │   │   ├── table.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── checkbox.tsx
│   │   │   ├── tabs.tsx
│   │   │   ├── label.tsx
│   │   │   └── textarea.tsx
│   │   └── layout/            # 布局组件
│   │       └── Layout.tsx
│   ├── features/              # 功能模块
│   │   ├── documents/         # 文档管理
│   │   ├── graph/             # 知识图谱
│   │   ├── retrieval/         # 检索测试
│   │   ├── dashboard/         # 仪表板
│   │   └── login/             # 登录页面
│   ├── stores/                # 状态管理
│   │   ├── auth.ts            # 认证状态
│   │   ├── graph.ts           # 图谱状态
│   │   ├── documents.ts       # 文档状态
│   │   └── settings.ts        # 设置状态
│   ├── lib/                   # 工具库
│   │   └── utils.ts
│   ├── App.tsx                # 应用入口
│   ├── main.tsx               # 主渲染
│   └── index.css              # 全局样式
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
└── index.html
```

## 功能特性

### 1. 文档管理 (Documents)
- 文档列表展示
- 文档状态跟踪 (pending/processing/processed/failed)
- 批量选择和删除
- 自动刷新
- 文档扫描

### 2. 知识图谱 (Graph)
- Sigma.js 可视化
- 力导向布局 (ForceAtlas2)
- 节点交互 (点击、悬停)
- 图谱数据展示

### 3. 检索测试 (Retrieval)
- 多模式查询 (naive/local/global/hybrid/mix)
- 流式响应
- 对话历史
- 实时显示

### 4. 仪表板 (Dashboard)
- 文档统计
- 系统健康状态
- 快速导航

### 5. 用户认证
- JWT认证
- 游客模式
- 登录/登出

## 快速开始

### 安装依赖

```bash
cd graphrag/frontend
npm install
# 或使用 bun
bun install
```

### 开发模式

```bash
npm run dev
# 或使用 bun
bun run dev
```

### 构建生产版本

```bash
npm run build
# 或使用 bun
bun run build
```

## 配置

### API 地址配置

在 `vite.config.ts` 中配置代理:

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:9621',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ''),
    },
  },
}
```

或在 `.env` 文件中设置:

```
VITE_API_URL=http://localhost:9621
```

## API 端点

前端与后端通过以下API交互:

### 认证
- `GET /auth-status` - 获取认证状态
- `POST /login` - 用户登录

### 文档
- `GET /documents` - 获取所有文档
- `POST /documents/upload` - 上传文档
- `POST /documents/scan` - 扫描文档
- `DELETE /documents` - 删除文档
- `GET /documents/pipeline_status` - 获取Pipeline状态

### 图谱
- `GET /graphs?label={label}&max_depth={depth}&max_nodes={nodes}` - 查询图谱
- `GET /graph/label/list` - 获取标签列表
- `GET /graph/label/search?q={query}` - 搜索标签

### 查询
- `POST /query` - 普通查询
- `POST /query/stream` - 流式查询

### 健康检查
- `GET /health` - 系统健康状态

## 迁移说明

本项目是从 LightRAG WebUI 迁移而来，主要改动包括:

1. **结构调整** - 采用 features 目录组织代码
2. **组件升级** - 使用最新的 Radix UI 组件
3. **状态管理** - 使用 Zustand 替代原有方案
4. **路由优化** - 使用 React Router v7
5. **样式统一** - 采用 Tailwind CSS + CSS 变量

## 开发指南

### 添加新组件

在 `src/components/ui/` 目录下添加新组件:

```typescript
// src/components/ui/new-component.tsx
import * as React from 'react'
import { cn } from '@/lib/utils'

export interface NewComponentProps extends React.HTMLAttributes<HTMLDivElement> {}

export const NewComponent = React.forwardRef<HTMLDivElement, NewComponentProps>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn('base-classes', className)}
        {...props}
      />
    )
  }
)
NewComponent.displayName = 'NewComponent'
```

### 添加新页面

在 `src/features/` 目录下创建新页面:

```typescript
// src/features/new-page/index.tsx
export default function NewPage() {
  return (
    <div>
      <h2>New Page</h2>
    </div>
  )
}
```

然后在 `App.tsx` 中添加路由:

```typescript
<Route path="/new-page" element={<NewPage />} />
```

## 注意事项

1. **Sigma.js 样式** - 需要导入 `@react-sigma/core/lib/style.css`
2. **Tailwind CSS** - 使用 CSS 变量实现主题切换
3. **API 代理** - 开发时使用 Vite 代理，生产环境需要配置 Nginx
4. **认证** - Token 存储在 localStorage，需要处理过期情况

## License

MIT
