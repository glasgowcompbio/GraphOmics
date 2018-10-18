import React from 'react'
import ReactDOM from 'react-dom'

class Welcome extends React.Component {
    render() {
        return <h1>Hello, {window.props.name}</h1>;
    }
}

const renderElement = <Welcome/>;
const mountElement = document.getElementById('summary-app');
ReactDOM.render(renderElement, mountElement);