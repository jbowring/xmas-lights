import PatternTable from "./PatternTable";
import React, {createRef} from "react";
import PatternModal from "./PatternModal"
import DeleteModal from "./DeleteModal";
import Schedule from "./Schedule";

class App extends React.Component {
    patternModal = createRef();
    deleteModal = createRef();

    constructor(props) {
        super(props);
        this.state = {
            now: new Date(),
            patterns: new Map(),
            schedule: new Map(),
            webSocketConnected: true,
        };
    }

    beginWebSocket(url) {
        this.webSocket = new WebSocket(url);

        this.webSocket.onclose = () => {
            this.webSocketTimeout = setTimeout(() => this.beginWebSocket(url), 1000);
            this.setState({
                webSocketConnected: false,
            })
        }
        this.webSocket.onmessage = (event) => {
            const data = JSON.parse(event.data)

            if(data.hasOwnProperty("patterns")) {
                this.setState({
                    patterns: new Map(Object.entries(data.patterns).map(([id, pattern]) => {
                        pattern.id = id
                        return [id, pattern]
                    }))
                })
            }

            if(data.hasOwnProperty("schedule")) {
                this.setState({schedule: new Map(Object.entries(data.schedule))})
            }
        }
        this.webSocket.onopen = () => {
            this.setState({
                webSocketConnected: true,
            })
        }
    }

    componentDidMount() {
        if(process.env.NODE_ENV === "development") {
            this.beginWebSocket("ws://127.0.0.1:5000/ws")
        } else {
            this.beginWebSocket((window.location.protocol === "https:" ? "wss://" : "ws://") + window.location.host + "/ws");
        }
        this.setState({now: new Date()})

        this.timer = setInterval(() => this.setState({now: new Date()}), 1000)
    }

    componentWillUnmount() {
        clearTimeout(this.webSocketTimeout)
        this.webSocket.onclose = null
        this.webSocket.close()

        clearInterval(this.timer)
    }

    editPattern = (patternId) => {
        this.patternModal.current.setState({
            currentPattern: this.state.patterns.get(patternId),
        });
    }

    deletePattern = (patternId) => {
        this.webSocket.send(JSON.stringify({
            action: 'delete',
            pattern: {
                id: patternId,
            },
        }))
        this.deleteModal.current.close()
    }

    newPattern = () => {
        this.patternModal.current.setState({
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

    sendPattern = (pattern) => {
        this.webSocket.send(JSON.stringify({
            action: 'update',
            pattern: pattern,
        }))
        this.patternModal.current.close()
    }

    setPatternActiveCallback = (patternId, active) => {
        this.webSocket.send(JSON.stringify({
            action: 'update',
            pattern: {
                id: patternId,
                active: active,
            },
        }))
    }

    confirmDelete = (patternId) => {
        this.deleteModal.current.setState({
            currentPattern: this.state.patterns.get(patternId),
        });
    }

    render() {
        let lightsEnabled = (this.state.schedule.get('status') ?? 'on') === 'on'

        return (
          <div>
              <h1 className="main-title">XMAS LIGHTS</h1>

              <Schedule
                  events={this.state.schedule.get('events') ?? []}
                  lightsEnabled={lightsEnabled}
                  todayWeekday={this.state.schedule.get('today_weekday')}
                  tomorrowWeekday={this.state.schedule.get('tomorrow_weekday')}
                  patterns={this.state.patterns} />
              <PatternTable
                  lightsEnabled={lightsEnabled}
                  patterns={this.state.patterns}
                  editCallback={this.editPattern}
                  deleteCallback={this.confirmDelete}
                  setPatternActiveCallback={this.setPatternActiveCallback}
              />
              <div style={{display: "flex"}}>
                  <button id="addButton" type="button" onClick={this.newPattern}>
                      +
                  </button>
              </div>
              <PatternModal ref={this.patternModal} submitCallback={this.sendPattern}/>
              <DeleteModal ref={this.deleteModal} deleteCallback={this.deletePattern}/>
              <div id="warning-div" className={this.state.webSocketConnected ? '' : "warning-active"}>
                  <div id="error-overlay" />
                  <div className="fixed-bottom text-light" id="warning-bar">
                      <h6 style={{"padding": "10px"}}>
                          <i className="bi bi-exclamation-triangle" style={{paddingRight: "10px"}} />
                          Connection to server lost, attempting to reconnect...
                      </h6>
                  </div>
              </div>
          </div>
        );
    }
}

export default App;
