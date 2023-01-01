import React, { useRef, useEffect } from 'react';
import * as monaco from 'monaco-editor';

window.MonacoEnvironment = {
	getWorkerUrl: function (_moduleId, label) {
		if (label === 'json') {
			return './json.worker.bundle.js';
		}
		if (label === 'css' || label === 'scss' || label === 'less') {
			return './css.worker.bundle.js';
		}
		if (label === 'html' || label === 'handlebars' || label === 'razor') {
			return './html.worker.bundle.js';
		}
		if (label === 'typescript' || label === 'javascript') {
			return './ts.worker.bundle.js';
		}
		return './editor.worker.bundle.js';
	}
};

export default function Editor(props) {
	const divEl = useRef(null);
	let editor = useRef(null);
	useEffect(() => {
		if (divEl.current) {
			editor.current = monaco.editor.create(divEl.current, {
				value: '',
				language: 'python',
				theme: 'vs-dark',
				minimap: {enabled: false},
				automaticLayout: true,
				lineNumbersMinChars: 3,
			});
		}

		editor.current.setValue(props.value);

		return () => editor.current.dispose();
	}, [props.value]);

	return <div id="monaco-editor-container" ref={divEl}></div>;
}