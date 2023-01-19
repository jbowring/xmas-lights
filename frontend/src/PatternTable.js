import React from "react";
import {OverlayTrigger, Tooltip} from "react-bootstrap";

function ErrorSymbol(props) {
    const error = props.pattern.hasOwnProperty('error') && props.pattern.error !== null;

    return (
        <OverlayTrigger
            placement="bottom"
            overlay={
                <Tooltip>
                    {props.pattern.error}
                </Tooltip>
            }
        >
            <button className="errorButton" style={{"visibility": error ? "visible" : "hidden"}}>
                <h6>
                    <i className="bi bi-exclamation-circle"/>
                </h6>
            </button>
        </OverlayTrigger>
    )
}

function playStopIcons() {
    return (
        <h5>
            <i className="bi bi-play-fill"/>
            <i className="bi bi-stop-fill"/>
        </h5>
    )
}

function scheduleIcon() {
    return <i style={{fontSize: "16px"}} className="bi bi-alarm"/>
}

function ActiveButton(props) {
    const active = props.pattern.hasOwnProperty('active') && props.pattern.active;

    return (
        <button
            type="button"
            className={"activeButton" + (active ? ' active' : '')}
            onClick={() => props.setPatternActiveCallback(props.pattern.id, !active)}
        >
            {props.lightsEnabled ? playStopIcons() : scheduleIcon()}
        </button>
    )
}

function PatternRows(props) {
    return Array.from(props.patterns.values()).sort((pattern1, pattern2) => {
        return pattern1.name.toLowerCase().localeCompare(pattern2.name.toLowerCase())
    }).map((pattern) => (
        <tr key={pattern.id} className="buttonParent">
            <td className="activeTd">
                <div className="activeDiv">
                    <ErrorSymbol pattern={pattern} />
                    <ActiveButton
                        lightsEnabled={props.lightsEnabled}
                        pattern={pattern}
                        setPatternActiveCallback={props.setPatternActiveCallback}
                    />
                </div>
            </td>
            <td>
                {pattern.name}
            </td>
            <td>
                {pattern.author}
            </td>
            <td>
                <div className="actionDiv">
                    <button type="button" className="editButton" title="Edit" onClick={() => props.editCallback(pattern.id)}>
                        <i className="bi bi-pencil-fill"></i>
                    </button>
                    <button type="button" className="deleteButton" title="Delete" onClick={() => props.deleteCallback(pattern.id)}>
                        <i className="bi bi-trash3-fill"></i>
                    </button>
                </div>
            </td>
        </tr>
    ))
}

class PatternTable extends React.Component {
    render() {
        return (
            <table className="table table-hover">
                <thead>
                    <tr>
                        <th>Status</th>
                        <th>Pattern Name</th>
                        <th>Author</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <PatternRows
                        lightsEnabled={this.props.lightsEnabled}
                        patterns={this.props.patterns}
                        editCallback={this.props.editCallback}
                        deleteCallback={this.props.deleteCallback}
                        setPatternActiveCallback={this.props.setPatternActiveCallback}
                    />
                </tbody>
            </table>
        )
    }
}

export default PatternTable;