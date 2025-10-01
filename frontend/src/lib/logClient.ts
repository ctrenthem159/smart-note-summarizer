interface ClientLog {
    level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'CRITICAL';
    message: string;
    timestamp: string;
    userAgent: string;
}

const CONSOLE_LEVELS = {
    debug: console.debug,
    log: console.log,
    warn: console.warn,
    error: console.error
}

const SERVER_LOG_ENDPOINT = 'http://127.0.0.1:8000/log/client'

export async function logClientMessage(message: string, level: ClientLog['level']): Promise<void> {
    const logData: ClientLog = {
        level: level,
        message: message,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
    };

    try {
        await fetch(SERVER_LOG_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(logData),
            keepalive: true,
        })
    } catch (e) {
        CONSOLE_LEVELS.warn('Failed to send client log to server:', e);
    }
}

export function initializeClientLogging() {
    console.debug = (...args: any[]) => {
        CONSOLE_LEVELS.log(...args);
        logClientMessage(String(args[0]), 'DEBUG')
    }

    console.log = (...args: any[]) => {
        CONSOLE_LEVELS.log(...args);
        logClientMessage(String(args[0]), 'INFO')
    }

    console.error = (...args: any[]) => {
        CONSOLE_LEVELS.error(...args);
        logClientMessage(String(args[0]), 'ERROR')
    }

    console.warn = (...args: any[]) => {
        CONSOLE_LEVELS.warn(...args);
        logClientMessage(String(args[0]), 'WARN')
    }

    window.onerror = (message, source, lineno, colno, error) => {
        const errorMsg = 'Uncaught Error: ${message} at ${source}:${lineno}';
        logClientMessage(errorMsg, 'ERROR');
        return true;
    };
}