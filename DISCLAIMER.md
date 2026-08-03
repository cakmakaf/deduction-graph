# Disclaimer

**This project is a software engineering demonstration. It is not tax advice.**

The system computes figures from rule parameters transcribed from public IRS
guidance. Those parameters are drafted and, until each one is individually
verified against its cited primary source, they may be wrong. Every response the
system produces reports which parameters it used that are not yet verified.

Do not rely on any output of this software for preparing or filing a tax return.
Consult a qualified tax professional or the relevant IRS publication directly.

## Data provenance

- The rule corpus is drawn from IRS publications, which are U.S. government works
  in the public domain.
- All taxpayer profiles in this repository are synthetic and generated
  programmatically. No real personally identifiable information is present, and
  none should ever be added.
- No employer data, proprietary code, or internal documentation of any kind is
  used in this project. The architecture demonstrated here is an independent,
  from-scratch implementation over public sources.

## Scope

Version 1 covers individual U.S. federal income tax deductions for tax years 2024
and 2025 only. It does not cover state returns, business returns, credits, or any
other tax year. The system is built to refuse questions outside that scope rather
than answer them approximately.
