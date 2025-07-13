
            const { processData } = require('./processor');

            function run() {
                const data = [1, 2, 3, null, 5];
                return processData(data);
            }

            module.exports = { run };
