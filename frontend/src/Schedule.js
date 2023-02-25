import React, {createRef} from "react";
import {Overlay, Popover} from "react-bootstrap";

class Select extends React.Component {
    render() {
        let output = []

        for(let i=0; i <= this.props.max; i++) {
            output.push(<option key={i} value={i}>
                {String(i).padStart(2, '0')}
            </option>)
        }

        return (
            <select
                className="form-select form-select-sm"
                style={{maxWidth: "max-content", marginLeft: "5px", minWidth: "max-content"}}
                value={this.props.selected}
                onChange={event => this.props.onChange(event.target.value)}
                ref={this.props.selectRef}
            >
                {output}
            </select>
        )
    }
}

class TimePicker extends React.Component {
    hourRef = createRef();
    minuteRef = createRef();

    render() {
        return (
            <>
                <div style={{alignSelf: "center", justifySelf: "end"}}>
                    {this.props.title}
                </div>
                <div style={{display: "flex", justifyContent: "flex-start"}}>
                    <Select
                        max={23}
                        selectRef={this.hourRef}
                        onChange={hour => this.props.onChange({
                            hour: hour,
                            minute: this.minuteRef.current.value,
                            action: this.props.event.action,
                        })}
                        selected={this.props.event.hour}
                    />
                    <Select
                        max={59}
                        selectRef={this.minuteRef}
                        onChange={minute => this.props.onChange({
                            hour: this.hourRef.current.value,
                            minute: minute,
                            action: this.props.event.action,
                        })}
                        selected={this.props.event.minute}
                    />
                </div>
            </>
        )
    }
}

export default class Schedule extends React.Component {
    state = { showSchedule: false}
    days = ["M", "T", "W", "T", "F", "S", "S"]
    overlayTargetRef = createRef();

    render() {
        const events = this.props.schedule.get('events') ?? []
        const lightsEnabled = this.props.lightsEnabled
        const todayWeekday = this.props.schedule.get('today_weekday')
        const tomorrowWeekday = this.props.schedule.get('tomorrow_weekday')
        const patternSelected = Array.from(this.props.patterns.values()).some(pattern => pattern.hasOwnProperty('active') && pattern.active)

        let next = events.find(pattern => pattern.action === (lightsEnabled && patternSelected ? "off" : "on"))
        if(next === undefined) {
            next = events[0]
        }

        let buttonText = 'No schedule'

        if(next !== undefined) {
            buttonText = `Turn ${next.action} at ${next.hour}:${String(next.minute).padStart(2, '0')}`

            if(next.day === tomorrowWeekday) {
                buttonText += " tomorrow"
            } else if(next.day !== todayWeekday) {
                buttonText += " on "
                buttonText += ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][next.day]
            }
        }

        const scheduleDays = [...new Set(events.map(event => event.day))]

        const dayButtons = this.days.map((day, index) => (
            <button
                key={index}
                className={"dayButton" + (scheduleDays.includes(index) ? " dayButtonActive" : "")}
                onClick={() => this.props.onScheduleChange({type: 'button', value: index})}
            >
                {day}
            </button>
        ))

        const onEvent = events.find(event => event.action === "on") ?? {hour: 0, minute: 0}
        const offEvent = events.find(event => event.action === "off") ?? {hour: 0, minute: 0}

        return (
            <div style={{display: "flex"}}>
                <button
                    ref={this.overlayTargetRef}
                    id="schedule-button"
                    className={patternSelected ? "" : "schedule-error"}
                    onClick={() => this.setState({showSchedule: !this.state.showSchedule})}
                >
                    <i className="bi bi-alarm" style={{marginRight: "7px", fontSize: "16px"}}/>
                    {buttonText}
                </button>
                <Overlay target={this.overlayTargetRef.current} show={this.state.showSchedule} placement="bottom">
                    <Popover style={{background: "aliceblue"}}>
                        <Popover.Body>
                            <div>
                                {dayButtons}
                            </div>
                            <div style={{textAlign: "center"}}>
                            <div className={"schedule-container"}>
                                <TimePicker
                                    title={"Turn on"}
                                    event={onEvent}
                                    onChange={time => this.props.onScheduleChange({type: 'time', value: time})}
                                />
                                <TimePicker
                                    title={"Turn off"}
                                    event={offEvent}
                                    onChange={time => this.props.onScheduleChange({type: 'time', value: time})}
                                />
                            </div>
                            </div>
                        </Popover.Body>
                    </Popover>
                </Overlay>
            </div>
        )
    }
}