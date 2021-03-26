pub mod cli;
pub mod error;
pub mod record;
use std::{
    fs::File,
    io::{BufRead, BufReader},
};

use cli::ReportOpts;
use error::Result;
use record::Record;
use structopt::StructOpt;

fn main() -> Result<()> {
    let opts = ReportOpts::from_args();
    let d = opts.monitor_dir;
    let file = File::open(d)?;
    let lines = BufReader::new(file).lines();
    for line in lines {
        let line = line?;
        println!("{}", line);
        let record: Record = serde_json::from_str(&line.trim_end())?;
        println!("{}", record.type_);
    }
    Ok(())
}
