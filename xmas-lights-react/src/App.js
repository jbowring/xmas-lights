import PatternTable from "./PatternTable";
import React, {createRef} from "react";
import PatternModal from "./PatternModal"

class App extends React.Component {
    modal = createRef();

    constructor(props) {
        super(props);
        this.state = {
            patterns: {},
        };
    }

    beginWebSocket(url) {
        this.webSocket = new WebSocket(url);

        this.webSocket.onclose = () => {
            setTimeout(() => this.beginWebSocket(url), 1000);
        }
        this.webSocket.onerror = () => {
            setTimeout(() => this.beginWebSocket(url), 1000);
        }
        this.webSocket.onmessage = (event) => {
            this.setState({patterns: JSON.parse(event.data)})
        }
    }

    componentDidMount() {
        if(process.env.NODE_ENV === "development") {
            this.beginWebSocket("ws://127.0.0.1:5000/ws")
        } else {
            this.beginWebSocket((window.location.protocol === "https:" ? "wss://" : "ws://") + window.location.host + "/ws");
        }
    }

    componentWillUnmount() {
        this.webSocket.close()
    }

    editPattern = (patternId) => {
        this.modal.current.setState({
            currentPattern: this.state.patterns[patternId],
        });
    }

    deletePattern = (patternId) => {
        this.webSocket.send(JSON.stringify({
            action: 'delete',
            pattern: {
                id: patternId,
            },
        }))
    }

    newPattern = () => {
        this.modal.current.setState({
            currentPattern: {
                id: null,
                name: 'name',
                author: 'author',
                script: [
                    'result = [[',
                    '	255 * (1 - (((seconds / 0.03) + led_index) % max_leds) / max_leds),',
                    '	100 * (1 - (((seconds / 0.03) + led_index) % max_leds) / max_leds),',
                    '	255 * (1 - (((seconds / 0.03) + led_index) % max_leds) / max_leds),',
                    '] for led_index in range(max_leds)]',
                ].join('\n'),
                active: false,
            },
        });
    }

    closeModal = () => {
        this.modal.current.setState({currentPattern: null})
    }

    sendPattern = (pattern) => {
        this.webSocket.send(JSON.stringify({
            action: 'update',
            pattern: pattern,
        }))
        this.closeModal()
    }

    render() {
        return (
          <div>
              <h1 className="main-title">XMAS LIGHTS</h1>
              <PatternTable patterns={this.state.patterns} editCallback={this.editPattern} deleteCallback={this.deletePattern}/>
              <div style={{display: "flex"}}>
                  <button id="addButton" type="button" onClick={this.newPattern}>
                      +
                  </button>
              </div>
              <PatternModal ref={this.modal} submitCallback={this.sendPattern} closeCallback={this.closeModal}/>
          </div>
        );
    }
}

export default App;
