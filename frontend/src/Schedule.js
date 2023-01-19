import React from "react";


export default class Schedule extends React.Component {
    render() {
        const patternSelected = Array.from(this.props.patterns.values()).some(pattern => pattern.hasOwnProperty('active') && pattern.active)

        let next = this.props.events.find(pattern => pattern.action === (this.props.lightsEnabled && patternSelected ? "off" : "on"))
        if(next === undefined) {
            next = this.props.events[0]
        }

        let buttonText = 'No schedule'

        if(next !== undefined) {
            buttonText = `Turn ${next.action} at ${next.hour}:${next.minute}`

            if(next.day === this.props.tomorrowWeekday) {
                buttonText += " tomorrow"
            } else if(next.day !== this.props.todayWeekday) {
                buttonText += " on "
                buttonText += ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][next.day]
            }
        }

        return (
            <div style={{display: "flex"}}>
                <button id="schedule-button" className={patternSelected ? "" : "schedule-error"} disabled={true}>
                    <i className="bi bi-alarm" style={{marginRight: "7px", fontSize: "16px"}}/>
                    {buttonText}
                </button>
            </div>
        )
    }
}