const minify = require('html-minifier').minify;
const fs = require('fs');

fs.readFile('index.html', 'utf8', function (err,data) {
    if (err) {
        return console.log(err);
    }

    let result = minify(data, {
        removeAttributeQuotes: true,
        minifyJS: true,
        minifyCSS: true,
        collapseWhitespace: true,
        removeComments: true,
    });

    fs.writeFile('index.min.html', result, 'utf8', function () {

    });
    ""
    pythonModule = `def generate_html(patterns_json):\n    return '''`
    pythonModule += result.replace(`'{"dsafqwwea": {"error": "Traceback (most recent call last):\\\\n File \\\\"main.py\\\\", line 252, in main\\\\n File \\\\"<string>\\\\", line 1\\\\n SyntaxError: invalid syntax ", "active": false, "author": "Joel", "name": "Static white", "date": "Today", "script": "return 255, 255, 255"}, "uihsaduha": {"active": true, "author": "Joel", "name": "Static green/red", "date": "Today", "script": "if led % 2 == 0:\\\\n    return 255, 0, 0\\\\nelse:\\\\n    return 0, 255, 0"}}'`, `''' + patterns_json + '''`);

    pythonModule += `'''`

    console.log(pythonModule)
    console.log(data.length)
    console.log(result.length)

    fs.writeFile('../xmas-lights-upython/html.py', pythonModule, 'utf8', function () {

    });
});