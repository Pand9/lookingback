pub mod cli;
pub mod error;
pub mod record;
pub mod summary;
use std::{
    fs::{self, File},
    io::{BufRead, BufReader},
    mem,
    path::PathBuf,
};

use chrono::{DateTime, Duration, DurationRound, Local, TimeZone};
use cli::ReportOpts;
use error::{Error, Result};
use record::{AssembledRecord, Record};
use structopt::StructOpt;
use summary::make_summary;

pub const FMT: &'static str = "monitor.%Y-%m-%d_%H:%M.log";

fn main() -> Result<()> {
    let opts = ReportOpts::from_args();
    let mut records: Vec<Record> = vec![];
    let paths = get_filenames(&opts)?;
    for path in &paths {
        let file = File::open(&path)?;
        let lines = BufReader::new(file).lines();
        for (i, line) in lines.enumerate() {
            let line = line?;
            let line = line.trim_end();
            if line.is_empty() {
                continue;
            }
            let record: Record = match serde_json::from_str(&line.trim_end()) {
                Ok(rec) => rec,
                Err(e) => {
                    log::info!(
                        "Problem {} with file {:?}, line {}: {}",
                        e,
                        path,
                        i,
                        &line[..100]
                    );
                    continue;
                }
            };
            records.push(record);
        }
    }
    let records = assemble(records)?;
    let record_chunks = split_chunks(records, opts.chunk_minutes)?;
    let mut summaries = vec![];
    for records in record_chunks {
        summaries.push(make_summary(records, &opts)?);
    }
    if opts.format == "simple" {
        for summary in summaries {
            println!("{}", summary);
        }
    } else if opts.format == "jsonstream" {
        for summary in summaries {
            println!("{}", serde_json::to_string(&summary)?);
        }
    } else if opts.format == "jsonpretty" {
        println!("{}", serde_json::to_string_pretty(&summaries)?);
    } else {
        eprintln!("unsupported format {}", opts.format);
    }
    Ok(())
}

fn get_filenames(opts: &ReportOpts) -> Result<Vec<PathBuf>> {
    let mut res = vec![];
    match fs::read_dir(&opts.monitor_dir) {
        Ok(dir_entries) => {
            for entry in dir_entries {
                let entry = match entry {
                    Ok(e) => e,
                    Err(error) => {
                        return Err(Error::from_file(
                            "read_dir iteration error",
                            &opts.monitor_dir,
                            error,
                        ))
                    }
                };
                let fname = entry.file_name().to_string_lossy().to_string();
                if !fname.starts_with("monitor.") {
                    continue;
                }
                let dtime: DateTime<Local> = extract_date(&fname)?;
                if opts.from > dtime {
                    continue;
                }
                if opts.to.map(|to| to <= dtime).unwrap_or(false) {
                    continue;
                }
                res.push(entry.path());
            }
        }
        Err(error) => {
            return Err(Error::from_file(
                "read_dir call error",
                &opts.monitor_dir,
                error,
            ))
        }
    };
    res.sort();
    Ok(res)
}

fn extract_date(s: &str) -> Result<DateTime<Local>> {
    Ok(Local.datetime_from_str(s, FMT)?)
}

fn assemble(records: Vec<Record>) -> Result<Vec<AssembledRecord>> {
    let mut res = vec![];
    let mut assrec: Option<AssembledRecord> = None;
    for record in records {
        match assrec.as_mut() {
            Some(assrec) => match record.type_.as_str() {
                "meta" => res.push(mem::replace(
                    assrec,
                    AssembledRecord::new(record.timestamp.unwrap()),
                )),
                "wmctrl_windows" => {
                    assrec.windows = record.windows;
                }
                "wmctrl_desktops" => {
                    assrec.desktops = record.desktops;
                }
                "xprintidle" => {
                    assrec.idle_msecs = record.idle_msecs;
                }
                "xdotool_active_window" => {
                    assrec.window_id = record.window_id;
                    assrec.window_title = record.window_title;
                }
                _ => {
                    return Err(Error::new(format!("unknown event type {:?}", record)));
                }
            },
            None if record.type_ == "meta" => {
                assert!(
                    None == mem::replace(
                        &mut assrec,
                        Some(AssembledRecord::new(record.timestamp.unwrap())),
                    )
                );
            }
            None => {
                return Err(Error::new2("first entry wasn't a meta"));
            }
        };
    }
    Ok(res)
}

fn split_chunks(
    recs: Vec<AssembledRecord>,
    chunk_minutes: u64,
) -> Result<Vec<Vec<AssembledRecord>>> {
    let duration = if chunk_minutes == 0 {
        None
    } else {
        Some(Duration::minutes(chunk_minutes as i64))
    };
    if recs.len() == 0 {
        Ok(vec![])
    } else {
        let mut res: Vec<Vec<AssembledRecord>> = vec![vec![]];
        let mut gcid = duration.map(|duration| {
            recs.first()
                .unwrap()
                .timestamp
                .duration_trunc(duration)
                .unwrap()
        });
        for rec in recs {
            if gcid.is_some() {
                let cid = rec.timestamp.duration_trunc(duration.unwrap()).unwrap();
                if cid != gcid.unwrap() {
                    gcid = Some(cid);
                    res.push(vec![]);
                }
            }
            res.last_mut().unwrap().push(rec);
        }
        Ok(res)
    }
}
