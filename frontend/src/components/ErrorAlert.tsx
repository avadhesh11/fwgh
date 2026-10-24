import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorAlertProps {
  message: string;
  onRetry: () => void;
}

export const ErrorAlert: React.FC<ErrorAlertProps> = ({ message, onRetry }) => {
  return (
    <div className="error-banner">
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <AlertTriangle size={20} color="#ef4444" />
        <div>
          <strong>Backend Service Communication Error</strong>
          <div style={{ fontSize: '0.82rem', marginTop: '2px', opacity: 0.9 }}>
            {message}
          </div>
        </div>
      </div>
      <button type="button" className="btn-retry" onClick={onRetry}>
        <RefreshCw size={12} style={{ display: 'inline', marginRight: '6px' }} />
        Retry
      </button>
    </div>
  );
};
