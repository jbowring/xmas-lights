import React from "react";
import Modal from "react-bootstrap/Modal";

export default class DeleteModal extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            currentPattern: null,
        }
    }

    close = () => {
        this.setState({currentPattern: null})
    }

    render() {
        let show = this.state.currentPattern !== null;

        return (
            <Modal show={show} centered onHide={() => this.setState({currentPattern: null})}>
                <Modal.Header>
                    <h1 className="modal-title fs-5">
                        Delete pattern?
                    </h1>
                </Modal.Header>
                <Modal.Body>
                    <div>
                        Are you sure you want to delete <b>{show ? this.state.currentPattern.name : ''}</b>?
                    </div>
                </Modal.Body>
                <Modal.Footer>
                    <button type="button" className="btn btn-secondary" onClick={this.close}>
                        Cancel
                    </button>
                    <button type="button" className="btn btn-danger" onClick={() => this.props.deleteCallback(this.state.currentPattern.id)}>
                        Delete
                    </button>
                </Modal.Footer>
            </Modal>
        )
    }
}