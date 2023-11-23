import React, {createRef} from "react";
import Editor, {loader} from "@monaco-editor/react";
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
    form = createRef();

    defaultState = () => {
        return {
            contentsModified: false,
            currentPattern: null,
            validated: false,
        }
    }

    constructor(props) {
        super(props);
        this.state = this.defaultState();
        loader.init();
    }

    close = () => {
        this.setState(this.defaultState())
    }

    checkContentsModified = () => {
        if(this.state.currentPattern !== null) {
            this.setState({
                contentsModified:
                    this.state.currentPattern.name !== this.editPatternName.current.value ||
                    this.state.currentPattern.author !== this.editPatternAuthor.current.value ||
                    this.state.currentPattern.script !== this.editPatternScript.current.getValue()
            })
        }
    }

    handleEditorDidMount = (editor, monaco) => {
        this.editPatternScript.current = editor;
        if(
            this.state.currentPattern.error &&
            this.state.currentPattern.error.mark_message &&
            Number.isInteger(this.state.currentPattern.error.line_number)
        ) {
            monaco.editor.removeAllMarkers("owner");
            monaco.editor.setModelMarkers(editor.getModel(), "owner", [{
                message: this.state.currentPattern.error.mark_message,
                severity: monaco.MarkerSeverity.Error,
                startLineNumber: this.state.currentPattern.error.line_number,
                endLineNumber: this.state.currentPattern.error.line_number,
                startColumn: 1,
                endColumn: editor.getModel().getLineLength(this.state.currentPattern.error.line_number) + 1,
            }])
        }
    }

    render() {
        let show = this.state.currentPattern !== null;

        return (
            <Modal size="lg" show={show} onHide={() => {
                if(!this.state.contentsModified) {
                    this.close()
                }
            }}>
                <Modal.Header>
                    <h1 className="modal-title fs-5">Edit pattern</h1>
                </Modal.Header>
                <Modal.Body>
                    <form ref={this.form} className={this.state.validated ? 'was-validated' : ''}>
                        <div className="form-group">
                            <label htmlFor="editPatternName">Pattern name:</label>
                            <input
                                ref={this.editPatternName}
                                className="form-control"
                                type="text"
                                defaultValue={show ? this.state.currentPattern.name : ''}
                                onInput={this.checkContentsModified}
                                required={true}
                            />
                        </div>
                        <br/>
                        <div className="form-group">
                            <label htmlFor="editPatternAuthor">Author:</label>
                            <input
                                ref={this.editPatternAuthor}
                                className="form-control"
                                type="text"
                                defaultValue={show ? this.state.currentPattern.author : ''}
                                onInput={this.checkContentsModified}
                                required={true}
                            />
                        </div>
                        <br/>
                        <div className="form-group">
                            <label htmlFor="monaco-editor-container">Code:</label>
                            <Instructions/>
                            <div id="monaco-editor-container">
                                <Editor
                                    value={show ? this.state.currentPattern.script : ''}
                                    language={'python'}
                                    theme={'vs-dark'}
                                    options={{
                                        minimap: {enabled: false},
                                        automaticLayout: true,
                                        lineNumbersMinChars: 3,
                                        renderWhitespace: "selection",
                                        detectIndentation: false,
                                        insertSpaces: true,
                                    }}
                                    onMount={this.handleEditorDidMount}
                                    onChange={this.checkContentsModified}
                                    />
                            </div>
                        </div>
                    </form>
                </Modal.Body>
                <Modal.Footer>
                    <button
                        type="button"
                        className={"btn btn-" + (this.state.contentsModified ? "danger" : "secondary")}
                        onClick={this.close}
                    >
                        {this.state.contentsModified ? "Discard changes" : "Close"}
                    </button>
                    <button
                        type="button"
                        className="btn btn-primary"
                        onClick={() => this.submit(this.props.submitCallback)}
                    >
                        Save changes
                    </button>
                </Modal.Footer>
            </Modal>
        )
    }

    submit = (submitCallback) => {
        if(this.form.current.checkValidity()) {
            submitCallback({
                id: this.state.currentPattern.id,
                name: this.editPatternName.current.value,
                author: this.editPatternAuthor.current.value,
                active: this.state.currentPattern.active,
                script: this.editPatternScript.current.getValue().split(/^/m).map(line =>
                    this.editPatternScript.current.getModel().normalizeIndentation(line)
                ).join(''),
            })
        } else {
            this.setState({
                validated: true,
            })
        }
    }
}