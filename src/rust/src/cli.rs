use std::path::PathBuf;

use crate::error::Result;
use chrono::{DateTime, Local, TimeZone};
use structopt::{clap::AppSettings, StructOpt};

#[derive(StructOpt, Debug, Clone)]
#[structopt(about = "Easytrack system activity log reducer", global_settings(&[AppSettings::DeriveDisplayOrder]))]
pub struct ReportOpts {
    #[structopt(
        long,
        parse(from_os_str),
        default_value = "/home/ks/workdir/trackdir/monitor/"
    )]
    pub monitor_dir: PathBuf,
    #[structopt(long, parse(try_from_str = parse_datetime), default_value = "2021-04-04_00:00")]
    pub from: DateTime<Local>,
    #[structopt(long, parse(try_from_str = parse_datetime))]
    pub to: Option<DateTime<Local>>,
    #[structopt(long, default_value = "0")]
    pub chunk_minutes: u64,
    #[structopt(long, default_value = "0")]
    pub chunk_colors: u64,
}

pub const FMT: &'static str = "%Y-%m-%d_%H:%M";

pub fn parse_datetime(s: &str) -> Result<DateTime<Local>> {
    Ok(Local.datetime_from_str(s, FMT)?)
}

pub fn from_args() -> ReportOpts {
    ReportOpts::from_args()
}
