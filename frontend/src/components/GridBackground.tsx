import styled from 'styled-components';

// 工作台底层网格背景。铺满父容器，所有卡片浮在其上。
// 网格线 #222 / 0.5px，对应原 Loader 的 grid-line 规格。
const GridBackground = () => {
  return <StyledWrapper />
}

const StyledWrapper = styled.div`
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(to right, #222 0.5px, transparent 0.5px),
    linear-gradient(to bottom, #222 0.5px, transparent 0.5px);
  background-size: 20px 20px;
  opacity: 0.6;
  -webkit-mask-image: linear-gradient(to bottom, transparent 0, #000 64px);
  mask-image: linear-gradient(to bottom, transparent 0, #000 64px);
`;

export default GridBackground;
