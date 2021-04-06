pub mod cli;
pub mod error;
pub mod record;
use std::{
    collections::HashMap,
    fmt::Display,
    fs::{self, File},
    io::{BufRead, BufReader},
    mem,
};

use chrono::{DateTime, Duration, DurationRound, Local, TimeZone};
use cli::ReportOpts;
use error::{Error, Result};
use record::{AssembledRecord, Record};
use structopt::StructOpt;

pub const FMT: &'static str = "monitor.%Y-%m-%d_%H:%M.log";

fn main() -> Result<()> {
    let opts = ReportOpts::from_args();
    let mut records: Vec<Record> = vec![];
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
                let dtime: DateTime<Local> = extract_date(&fname)?;
                if opts.from > dtime {
                    continue;
                }
                if opts.to.map(|to| to <= dtime).unwrap_or(false) {
                    continue;
                }
                let file = File::open(&entry.path())?;
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
                                entry.path(),
                                i,
                                &line[..100]
                            );
                            continue;
                        }
                    };

                    records.push(record);
                }
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
    let records = assemble(records)?;
    let record_chunks = split_chunks(records, opts.chunk_minutes)?;
    let mut summaries = vec![];
    for records in record_chunks {
        summaries.push(make_summary(records, &opts)?);
    }
    for summary in summaries {
        println!("{}", summary);
    }
    Ok(())
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

struct Summary {
    pub dt: DateTime<Local>,
    pub parts: Vec<SummaryPart>,
}

impl Display for Summary {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(f, "Bucket {}:\n", self.dt.format(FMT))?;
        for (i, part) in self.parts.iter().enumerate() {
            write!(
                f,
                "{}: \"{}\". {}s busy, {}s idle\n",
                i + 1,
                part.tag,
                part.ticks,
                part.idle_ticks
            )?;
        }
        Ok(())
    }
}

struct SummaryPart {
    pub tag: String,
    pub ticks: u64,
    pub idle_ticks: u64,
}

fn make_summary(recs: Vec<AssembledRecord>, opts: &ReportOpts) -> Result<Summary> {
    assert!(!recs.is_empty());
    let dt = if opts.chunk_minutes == 0 {
        opts.from.clone()
    } else {
        let duration = Duration::minutes(opts.chunk_minutes as i64);
        recs.first()
            .unwrap()
            .timestamp
            .duration_trunc(duration)
            .unwrap()
    };
    let mut groups: HashMap<String, (u64, u64)> = Default::default();
    for rec in recs {
        let tag = rec.window_title.unwrap_or("no window".to_owned());
        let idle = rec.idle_msecs.unwrap_or(0) >= 1000;
        let mut entry = groups.entry(tag.clone()).or_default();
        if idle {
            entry.1 += 1;
        } else {
            entry.0 += 1;
        }
    }
    let mut groups: Vec<(String, (u64, u64))> = groups.into_iter().collect();
    groups.sort_by_key(|e| -((e.1 .0 + e.1 .1) as i64));
    if opts.chunk_colors != 0 {
        groups.truncate(opts.chunk_colors as usize);
    }
    let groups = groups
        .into_iter()
        .map(|e| SummaryPart {
            tag: e.0,
            ticks: e.1 .0,
            idle_ticks: e.1 .1,
        })
        .collect();
    Ok(Summary { dt, parts: groups })
}
