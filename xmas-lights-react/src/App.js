import PatternTable from "./PatternTable";
import React from "react";
import PatternModal from "./PatternModal"

class App extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            patterns: {},
            currentPattern: null,
            showModal: false,
        };
        if(process.env.NODE_ENV === "development") {
            this.webSocket = new WebSocket("ws://127.0.0.1:5000/ws");
        } else {
            this.webSocket = new WebSocket((window.location.protocol === "https:" ? "wss://" : "ws://") + window.location.host + "/ws");
        }
        this.webSocket.onmessage = (event) => {
            this.state.patterns = JSON.parse(event.data);
        }
    }

    componentDidMount() {
        this.webSocket.onmessage = (event) => {
            this.setState({patterns: JSON.parse(event.data)})
        }
    }

    editPattern = (patternId) => {
        this.setState({
            currentPattern: this.state.patterns[patternId],
            showModal: true,
        });
    }

    newPattern = () => {
        this.setState({
            showModal: true,
            currentPattern: {
                name: 'name',
                author: 'author',
                script: [
                    'result = [[',
                    '	255 * (1 - (((seconds / 0.03) + led_index) % max_leds) / max_leds),',
                    '	100 * (1 - (((seconds / 0.03) + led_index) % max_leds) / max_leds),',
                    '	255 * (1 - (((seconds / 0.03) + led_index) % max_leds) / max_leds),',
                    '] for led_index in range(max_leds)]',
                ].join('\n'),
            },
        });
    }

    closeModal = () => {
        this.setState({currentPattern: null})
    }

    render() {
        return (
          <div>
              <h1 className="main-title">XMAS LIGHTS</h1>
              <PatternTable patterns={this.state.patterns} editCallback={this.editPattern}/>
              <div style={{display: "flex"}}>
                  <button id="addButton" type="button" onClick={this.newPattern}>
                      +
                  </button>
              </div>
              <PatternModal pattern={this.state.currentPattern} closeCallback={this.closeModal}/>
          </div>
        );
    }
}

export default App;
