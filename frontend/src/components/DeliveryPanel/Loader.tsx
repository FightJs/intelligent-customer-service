import styled from 'styled-components';

const Loader = () => {
  return (
    <StyledWrapper>
      <div className="main-container">
        <div className="loader">
          <svg viewBox="80 40 740 480" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">
            <defs>
              <linearGradient id="traceGradient1" x1={250} y1={120} x2={100} y2={200} gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#00ccff" stopOpacity={1} />
                <stop offset="100%" stopColor="#00ccff" stopOpacity={0.5} />
              </linearGradient>
              <linearGradient id="traceGradient2" x1={650} y1={120} x2={800} y2={300} gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#00ccff" stopOpacity={1} />
                <stop offset="100%" stopColor="#00ccff" stopOpacity={0.5} />
              </linearGradient>
              <linearGradient id="traceGradient3" x1={250} y1={380} x2={400} y2={400} gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#00ccff" stopOpacity={1} />
                <stop offset="100%" stopColor="#00ccff" stopOpacity={0.5} />
              </linearGradient>
              <linearGradient id="traceGradient4" x1={650} y1={120} x2={500} y2={100} gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#00ccff" stopOpacity={1} />
                <stop offset="100%" stopColor="#00ccff" stopOpacity={0.5} />
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
            <g id="traces">
              <path d="M100 300 H250 V120" className="trace-flow" />
              <path d="M800 200 H650 V380" className="trace-flow" />
              <path d="M400 520 V380 H250" className="trace-flow" />
              <path d="M500 50 V120 H650" className="trace-flow" />
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

  #browser {
    overflow: hidden;
  }

  .browser-frame {
    fill: #111;
    stroke: #666;
    stroke-width: 1;
    filter: drop-shadow(0 0 10px rgba(0, 0, 0, 0.9));
  }

  .browser-top {
    fill: #1a1a1a;
  }

  .loading-text {
    font-family: Haettenschweiler, sans-serif;
    font-size: 14px;
    fill: #e4e4e4;
  }

  .skeleton {
    fill: #2d2d2d;
    rx: 4;
    ry: 4;
    animation: pulse 1.8s ease-in-out infinite;
    filter: drop-shadow(0 0 3px rgba(255, 255, 255, 0.02));
  }

  @keyframes pulse {
    0% {
      fill: #2d2d2d;
    }
    50% {
      fill: #505050;
    }
    100% {
      fill: #2d2d2d;
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
    color: #00ccff;
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
