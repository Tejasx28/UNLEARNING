import React from 'react';
import ReactDOM from 'react-dom/client';
import { MotionConfig } from 'framer-motion';
import App from './App';
import './styles.css';
import './studio.css';
import './polish.css';
import './presentation-demos.css';
import './professional.css';
import './workspace-refresh.css';
import './demo-refresh.css';

class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { error: string }> {
  state = { error: '' };
  static getDerivedStateFromError(error: Error) { return { error: error.message }; }
  render() {
    if (this.state.error) return <main className="fatal studio" data-theme="light"><div className="brand-symbol">ATU</div><h1>The workspace could not load.</h1><p>Reload to reconnect. Reloading does not clear your saved run history.</p><details><summary>Technical details</summary><p>{this.state.error}</p></details><button className="button primary" onClick={() => location.reload()}>Reload workspace</button></main>;
    return this.props.children;
  }
}
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><ErrorBoundary><MotionConfig reducedMotion="user"><App /></MotionConfig></ErrorBoundary></React.StrictMode>);
