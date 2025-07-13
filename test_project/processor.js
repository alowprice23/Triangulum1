
            function processData(items) {
                // BUG: Doesn't check for null values
                return items.map(item => item * 2);
            }

            module.exports = { processData };
