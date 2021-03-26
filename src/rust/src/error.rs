#[derive(Debug, Clone, Eq, PartialEq)]
pub struct Error {
    pub msg: String,
}

pub type Result<T> = std::result::Result<T, Error>;

impl Error {
    pub fn new(msg: String) -> Self {
        Self { msg }
    }
    pub fn new2(msg: &str) -> Self {
        Self {
            msg: msg.to_owned(),
        }
    }
    pub fn from<E: std::error::Error>(msg: &str, err: E) -> Self {
        Self {
            msg: format!("{}; error: {:?}", msg, err),
        }
    }
}
impl std::fmt::Display for Error {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(f, "app error = {}", self.msg)
    }
}

impl std::error::Error for Error {}

impl From<serde_json::Error> for Error {
    fn from(e: serde_json::Error) -> Self {
        Self {
            msg: format!("JSON error: {:?}", e),
        }
    }
}

impl From<std::io::Error> for Error {
    fn from(e: std::io::Error) -> Self {
        Self {
            msg: format!("IO error: {:?}", e),
        }
    }
}

impl From<chrono::ParseError> for Error {
    fn from(e: chrono::ParseError) -> Self {
        Self {
            msg: format!("Chrono error: {:?}", e),
        }
    }
}
