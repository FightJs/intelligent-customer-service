import styled from 'styled-components';

const Loader = () => {
  return (
    <StyledWrapper>
      <div className="main-container">
        <div className="loader">
          <svg viewBox="250 120 400 260" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">
            <defs>
              <linearGradient id="traceGradient1" x1={250} y1={120} x2={100} y2={200} gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="currentColor" stopOpacity={1} />
                <stop offset="100%" stopColor="currentColor" stopOpacity={0.5} />
              </linearGradient>
              <linearGradient id="traceGradient2" x1={650} y1={120} x2={800} y2={300} gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="currentColor" stopOpacity={1} />
                <stop offset="100%" stopColor="currentColor" stopOpacity={0.5} />
              </linearGradient>
              <linearGradient id="traceGradient3" x1={250} y1={380} x2={400} y2={400} gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="currentColor" stopOpacity={1} />
                <stop offset="100%" stopColor="currentColor" stopOpacity={0.5} />
              </linearGradient>
              <linearGradient id="traceGradient4" x1={650} y1={120} x2={500} y2={100} gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="currentColor" stopOpacity={1} />
                <stop offset="100%" stopColor="currentColor" stopOpacity={0.5} />
              </linearGradient>
            </defs>
            <g id="browser">
              <rect x={250} y={120} width={400} height={260} rx={8} ry={8} className="browser-frame" />
              <rect x={250} y={120} width={400} height={30} rx={8} ry={8} className="browser-top" />
              <text x={294} y={140} textAnchor="middle" className="loading-text">
                Loading...
              </text>
              <rect x={270} y={160} width={360} height={20} className="skeleton" />
              <rect x={270} y={190} width={200} height={15} className="skeleton" />
              <rect x={270} y={215} width={300} height={15} className="skeleton" />
              <rect x={270} y={240} width={360} height={90} className="skeleton" />
              <rect x={270} y={340} width={180} height={20} className="skeleton" />
            </g>
          </svg>
        </div>
      </div>
    </StyledWrapper>
  );
}

const StyledWrapper = styled.div`
  .main-container {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100%;
    width: 100%;
    overflow: hidden;
  }

  .loader {
    width: 100%;
    height: 100%;
  }

  .loader svg {
    display: block;
    width: 100%;
    height: 100%;
    color: rgb(var(--color-accent));
  }

  #browser {
    overflow: hidden;
  }

  .browser-frame {
    fill: rgb(var(--color-surface));
    stroke: rgb(var(--color-outline));
    stroke-width: 1;
    filter: drop-shadow(0 0 10px rgba(0, 0, 0, 0.9));
  }

  .browser-top {
    fill: rgb(var(--color-active-surface));
  }

  .loading-text {
    font-family: Haettenschweiler, sans-serif;
    font-size: 14px;
    fill: rgb(var(--color-primary));
  }

  .skeleton {
    fill: rgb(var(--color-idle));
    rx: 4;
    ry: 4;
    animation: pulse 1.8s ease-in-out infinite;
    filter: drop-shadow(0 0 3px rgba(255, 255, 255, 0.02));
  }

  @keyframes pulse {
    0% {
      fill: rgb(var(--color-idle));
    }
    50% {
      fill: rgb(var(--color-active-surface));
    }
    100% {
      fill: rgb(var(--color-idle));
    }
  }

  .trace-flow {
    stroke-width: 1;
    fill: none;
    stroke-dasharray: 120 600;
    stroke-dashoffset: 720;
    animation: flow 5s linear infinite;
    opacity: 0.95;
    stroke-linejoin: round;
    filter: drop-shadow(0 0 8px currentColor) blur(0.5px);
    color: rgb(var(--color-accent));
  }
  .trace-flow:nth-child(1) {
    stroke: url(#traceGradient1);
  }
  .trace-flow:nth-child(2) {
    stroke: url(#traceGradient2);
  }
  .trace-flow:nth-child(3) {
    stroke: url(#traceGradient3);
  }
  .trace-flow:nth-child(4) {
    stroke: url(#traceGradient4);
  }

  @keyframes flow {
    from {
      stroke-dashoffset: 720;
    }
    to {
      stroke-dashoffset: 0;
    }
  }`;

export default Loader;
