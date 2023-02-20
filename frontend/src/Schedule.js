import React, {createRef} from "react";
import {Overlay, Popover} from "react-bootstrap";


export default class Schedule extends React.Component {
    target = createRef();

    constructor(props) {
        super(props);
        this.state = {
            showSchedule: true, // TODO change
        }
    }

    render() {
        const patternSelected = Array.from(this.props.patterns.values()).some(pattern => pattern.hasOwnProperty('active') && pattern.active)

        let next = this.props.events.find(pattern => pattern.action === (this.props.lightsEnabled && patternSelected ? "off" : "on"))
        if(next === undefined) {
            next = this.props.events[0]
        }

        let buttonText = 'No schedule'

        if(next !== undefined) {
            buttonText = `Turn ${next.action} at ${next.hour}:${String(next.minute).padStart(2, '0')}`

            if(next.day === this.props.tomorrowWeekday) {
                buttonText += " tomorrow"
            } else if(next.day !== this.props.todayWeekday) {
                buttonText += " on "
                buttonText += ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][next.day]
            }
        }

        const days = ["M", "T", "W", "T", "F", "S", "S"];
        const scheduleDays = [...new Set(this.props.events.map(event => event.day))]

        const dayButtons = days.map((day, index) => (
            <button key={index} className={"dayButton" + (scheduleDays.includes(index) ? " dayButtonActive" : "")}>
                {days[index]}
            </button>
        ))

        const onEvent = this.props.events.find(event => event.action === "on") ?? {hour: 0, minute: 0}
        const offEvent = this.props.events.find(event => event.action === "off") ?? {hour: 0, minute: 0}

        return (
            <div style={{display: "flex"}}>
                <button
                    ref={this.target}
                    id="schedule-button"
                    className={patternSelected ? "" : "schedule-error"}
                    onClick={() => this.setState({showSchedule: !this.state.showSchedule})}
                >
                    <i className="bi bi-alarm" style={{marginRight: "7px", fontSize: "16px"}}/>
                    {buttonText}
                </button>
                <Overlay target={this.target.current} show={this.state.showSchedule} placement="bottom">
                    <Popover style={{background: "aliceblue"}}>
                        <Popover.Body>
                            {dayButtons}
                            Turn on: {String(onEvent.hour).padStart(2, '0')}:{String(onEvent.minute).padStart(2, '0')}&nbsp;
                            Turn off: {String(offEvent.hour).padStart(2, '0')}:{String(offEvent.minute).padStart(2, '0')}
                        </Popover.Body>
                    </Popover>
                </Overlay>
            </div>
        )
    }
}