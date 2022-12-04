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
    console.log(result)
    console.log(data.length)
    console.log(result.length)

    fs.writeFile('index.min.html', result, 'utf8', function () {

    });

    result = result.replace(`'{"dsafqwwea": {"active": false, "author": "Joel", "name": "Static white", "date": "Today", "script": "return 255, 255, 255"}, "uihsaduha": {"active": true, "author": "Joel", "name": "Static green/red", "date": "Today", "script": "if led % 2 == 0:\\\\n    return 255, 0, 0\\\\nelse:\\\\n    return 0, 255, 0"}}'`, `''' + json.dumps(json.dumps(patterns)) + '''`);
    
    fs.writeFile('index.upython.html', result, 'utf8', function () {

    });
});