'use strict';
const { handle } = require('../server/report-delivery.cjs');
module.exports = async function reportAccess(req,res) {
  return handle(req,res);
};
