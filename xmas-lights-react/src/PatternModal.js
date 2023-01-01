import React, {createRef} from "react";
import Editor from "./Editor";
import Modal from 'react-bootstrap/Modal';

function Instructions() {
    return (
        <details>
            <summary>Instructions</summary>
            <div className="details-text">
                <b>Pre-imported modules</b>
                <p>
                    <code>math</code><br />
                    <code>random</code>
                </p>
                <b>Parameters</b>
                <p>
                    <code>max_leds -> int </code> Number of LEDs in the string<br />
                    <code>seconds -> float </code> Elapsed time (in seconds) since
                    the pattern started
                </p>
                <b>Output</b>
                <p>
                    Put a list of <code>max_leds * [R, G, B]</code> values into a
                    variable called <code>result</code>, where each value is between
                    0 and 255
                </p>
                <b>Note</b>
                <p>
                    Any variables declared in the global namespace remain for the
                    duration of the pattern and are available in future calls
                </p>
            </div>
        </details>
    )
}

export default class PatternModal extends React.Component {
    editPatternName = createRef();
    editPatternAuthor = createRef();
    editPatternScript = createRef();

    constructor(props) {
        super(props);
        this.state = {
            currentPattern: null,
        }
    }

    render() {
        let show = this.state.currentPattern !== null;

        return (
            <Modal size="lg" show={show}>
                <Modal.Header>
                    <h1 className="modal-title fs-5" id="editPatternModalLabel">Edit pattern</h1>
                    <button type="button" className="btn-close" data-bs-dismiss="modal"
                            aria-label="Close"></button>
                </Modal.Header>
                <Modal.Body>
                    <form>
                        <div className="form-group">
                            <label htmlFor="editPatternName">Pattern name:</label>
                            <input className="form-control" ref={this.editPatternName} type="text"
                                   defaultValue={show ? this.state.currentPattern.name : ''}/>
                        </div>
                        <br/>
                        <div className="form-group">
                            <label htmlFor="editPatternAuthor">Author:</label>
                            <input className="form-control" ref={this.editPatternAuthor} type="text"
                                   defaultValue={show ? this.state.currentPattern.author : ''}/>
                        </div>
                        <br/>
                        <div className="form-group">
                            <label htmlFor="monaco-editor-container">Code:</label>
                            <Instructions/>
                            <Editor editorRef={this.editPatternScript} value={show ? this.state.currentPattern.script : ''}/>
                        </div>
                    </form>
                </Modal.Body>
                <Modal.Footer>
                    <button type="button" className="btn btn-secondary" onClick={this.props.closeCallback}>
                        Close
                    </button>
                    <button type="button" className="btn btn-primary" onClick={() => this.submit(this.props.submitCallback)}>
                        Save changes
                    </button>
                </Modal.Footer>
            </Modal>
        )
    }

    submit = (submitCallback) => {
        submitCallback({
            id: this.state.currentPattern.id,
            name: this.editPatternName.current.value,
            author: this.editPatternAuthor.current.value,
            script: this.editPatternScript.current.getValue(),
            active: this.state.currentPattern.active,
        })
    }
}