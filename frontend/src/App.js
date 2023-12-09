import PatternTable from "./PatternTable";
import React, {createRef} from "react";
import PatternModal from "./PatternModal"
import DeleteModal from "./DeleteModal";
import Schedule from "./Schedule";

export default class App extends React.Component {
    patternModal = createRef();
    deleteModal = createRef();

    constructor(props) {
        super(props);
        this.state = {
            now: new Date(),
            patterns: new Map(),
            schedule: new Map(),
            updateRate: 0,
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
                this.setState({
                    schedule: new Map(Object.entries(data.schedule)),
                })
            }

            if(data.hasOwnProperty("update_rate")) {
                this.setState({
                    updateRate: data.update_rate,
                })
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
            this.beginWebSocket((window.location.protocol === "https:" ? "wss://" : "ws://") + "ws." + window.location.host);
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

    onScheduleChange = (scheduleChange) => {
        let schedule = this.state.schedule ?? new Map()
        let events = schedule.get('events') ?? []
        let days = new Set(events.map(event => event.day))

        if(scheduleChange.type === 'button' && !days.delete(scheduleChange.value)) {
            days.add(scheduleChange.value)
        }

        const newEvents = ["on", "off"].map(action => {
            let hour = 0
            let minute = 0

            if(scheduleChange.type === "time" && scheduleChange.value.action === action) {
                hour = parseInt(scheduleChange.value.hour)
                minute = parseInt(scheduleChange.value.minute)
            } else {
                let existingEvent = events.find(event => event.action === action)
                if(existingEvent !== undefined) {
                    hour = existingEvent.hour
                    minute = existingEvent.minute
                }
            }

            return [...days].map(day => {
                return {
                    day: day,
                    hour: hour,
                    minute: minute,
                    action: action,
                }
            })
        }).flat()

        let newSchedule = new Map(this.state.schedule)
        newSchedule.set("events", newEvents)

        this.webSocket.send(JSON.stringify({
            action: 'update_schedule',
            payload: Object.fromEntries(newSchedule),
        }))

        this.setState({
            schedule: newSchedule,
        })
    }

    editPattern = (patternId) => {
        this.patternModal.current.setState({
            currentPattern: this.state.patterns.get(patternId),
        });
    }

    deletePattern = (patternId) => {
        this.webSocket.send(JSON.stringify({
            action: 'delete_pattern',
            payload: {
                id: patternId,
            },
        }))
        this.deleteModal.current.close()
    }

    newPattern = () => {
        this.patternModal.current.setState({
            currentPattern: {
                id: null,
                name: '',
                author: '',
                script: [
                    '# Example pattern',
                    '',
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
            action: 'update_pattern',
            payload: pattern,
        }))
        this.patternModal.current.close()
    }

    setPatternActiveCallback = (patternId, active) => {
        this.webSocket.send(JSON.stringify({
            action: 'update_pattern',
            payload: {
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
        const lightsEnabled = (this.state.schedule.get('status') ?? 'on') === 'on'

        return (
          <div>
              <h1 className="main-title">XMAS LIGHTS</h1>
              <div
                  style={{position: "absolute", top: 0, left: 5, color: "lightgray", display: "flex", alignItems: "baseline"}}
                  hidden={!this.state.updateRate}
              >
                  <h2 style={{margin: 0}}>{this.state.updateRate ? this.state.updateRate : ""}</h2>
                  <h6>&nbsp;FPS</h6>
              </div>

              <Schedule
                  patterns={this.state.patterns}
                  schedule={this.state.schedule}
                  lightsEnabled={lightsEnabled}
                  onScheduleChange={this.onScheduleChange}
              />
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