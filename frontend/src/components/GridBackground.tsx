import styled from 'styled-components';

// 工作台底层网格背景。铺满父容器，所有卡片浮在其上。
// 深色辅助主题保留细网格，浅色青瓷主题由 index.css 隐藏。
const GridBackground = () => {
  return <StyledWrapper className="workbench-grid" />
}

const StyledWrapper = styled.div`
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(to right, rgb(var(--color-outline) / .55) 0.5px, transparent 0.5px),
    linear-gradient(to bottom, rgb(var(--color-outline) / .55) 0.5px, transparent 0.5px);
  background-size: 20px 20px;
  opacity: 0.6;
  -webkit-mask-image: linear-gradient(to bottom, transparent 0, #000 64px);
  mask-image: linear-gradient(to bottom, transparent 0, #000 64px);
`;

export default GridBackground;
