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

function ActiveButton(props) {
    const active = props.pattern.hasOwnProperty('active') && props.pattern.active;

    return (
        <button type="button" className={"activeButton" + (active ? ' active' : '')}>
            <h5>
                <i className="bi bi-play-fill"/>
                <i className="bi bi-stop-fill"/>
            </h5>
        </button>
    )
}

function PatternRows(props) {
    return Object.entries(props.patterns).map(([patternId, pattern]) => (
        <tr key={patternId} className="buttonParent">
            <td className="activeTd">
                <div className="activeDiv">
                    <ErrorSymbol pattern={pattern} />
                    <ActiveButton pattern={pattern} />
                </div>
            </td>
            <td>
                {pattern.name}
            </td>
            <td>
                {pattern.author}
            </td>
            <td>
                <button type="button" className="editButton" onClick={() => props.editCallback(patternId)}>
                    Edit
                </button>
                <button type="button" className="deleteButton">
                    Delete
                </button>
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
                    <PatternRows patterns={this.props.patterns} editCallback={this.props.editCallback}/>
                </tbody>
            </table>
        )
    }
}

export default PatternTable;