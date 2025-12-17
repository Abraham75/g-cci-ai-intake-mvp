// A Functional Reactive Programming (FRP) approach for the template-literal rendering engine in app.js

// Mock of a template-literal rendering engine
class RenderEngine {
    constructor(rootSelector) {
        this.root = document.querySelector(rootSelector);
    }

    render(template) {
        this.root.innerHTML = template;
    }
}

// Utility functions for creating reactive streams
const createStream = (initialValue) => {
    const listeners = [];
    let value = initialValue;

    return {
        subscribe: (listener) => listeners.push(listener),
        next: (newValue) => {
            value = newValue;
            listeners.forEach(listener => listener(value));
        },
        getValue: () => value,
    };
};

// Instantiating the rendering engine
const engine = new RenderEngine('#app');

// Stream for application state
const appState = createStream({ message: 'Welcome to the FRP-powered App!' });

// Subscribe to state changes and render
appState.subscribe((state) => {
    const template = `
        <div>
            <h1>${state.message}</h1>
        </div>
    `;
    engine.render(template);
});

// Example: Update state after 3 seconds
setTimeout(() => {
    appState.next({ message: 'State has been updated dynamically!' });
}, 3000);