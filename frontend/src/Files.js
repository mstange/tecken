/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 */
import React from "react";
import { Link } from "react-router-dom";

import {
  Loading,
  DisplayDate,
  formatFileSize,
  Pagination,
  BooleanIcon,
  TableSubTitle,
  thousandFormat,
  formatSeconds,
  DisplayDateDifference,
  filterToQueryString,
  parseQueryString,
} from "./Common";
import Fetch from "./Fetch";
import "./Upload.css"; // they have enough in common
import "./Files.css";

import store from "./Store";

class Files extends React.PureComponent {
  constructor(props) {
    super(props);
    this.pageTitle = "All Files";
    this.state = {
      loadingFiles: true, // undone by componentDidMount
      loadingAggregates: true,
      files: null,
      hasNextPage: false,
      total: null,
      batchSize: null,
      apiUrl: null,
      filter: {},
    };
  }

  componentWillMount() {
    store.resetApiRequests();
  }

  componentDidMount() {
    document.title = this.pageTitle;
    if (this.props.location.search) {
      this.setState(
        { filter: parseQueryString(this.props.location.search) },
        () => {
          this._fetchFilesAndAggregatesAsync(false);
        }
      );
    } else {
      this._fetchFilesAndAggregatesAsync(false);
    }
  }

  _fetch = (url, callback, errorCallback, updateHistory = true) => {
    const qs = filterToQueryString(this.state.filter);

    if (qs) {
      url += "?" + qs;
    }
    this.props.history.push({ search: qs });

    Fetch(url).then((r) => {
      if (this.setLoadingTimer) {
        window.clearTimeout(this.setLoadingTimer);
      }
      if (r.status === 403 && !store.currentUser) {
        store.setRedirectTo(
          "/",
          `You have to be signed in to view "${this.pageTitle}"`
        );
        return;
      }
      if (r.status === 200) {
        if (store.fetchError) {
          store.fetchError = null;
        }
        return r.json().then((response) => callback(response));
      } else {
        store.fetchError = r;
        if (errorCallback) {
          errorCallback();
        }
      }
    });
  };

  _fetchFilesAndAggregatesAsync = (updateHistory = true) => {
    this._fetchFiles(updateHistory);
    this._fetchAggregates();
  };

  _fetchFiles = (updateHistory = true) => {
    var callback = (response) => {
      this.setState({
        files: response.files,
        hasNextPage: response.has_next,
        batchSize: response.batch_size,
      });
      this.setState({ loadingFiles: false });
    };
    var errorCallback = () => {
      this.setState({ loadingFiles: false });
    };
    this.setState({ loadingFiles: true });
    this._fetch(
      "/api/uploads/files/content/",
      callback,
      errorCallback,
      updateHistory
    );
  };

  _fetchAggregates = () => {
    var callback = (response) => {
      this.setState({
        aggregates: response.aggregates,
        total: response.total,
      });
      this.setState({ loadingAggregates: false });
    };
    var errorCallback = () => {
      this.setState({ loadingAggregates: false });
    };
    this.setState({ loadingAggregates: true });
    this._fetch("/api/uploads/files/aggregates/", callback, errorCallback);
  };

  filterOnAll = (event) => {
    event.preventDefault();
    const filter = this.state.filter;
    // delete filter.user
    delete filter.download;
    filter.page = 1;
    filter.key = "";
    filter.size = "";
    this.setState({ filter: filter }, this._fetchFilesAndAggregatesAsync);
  };

  updateFilter = (newFilters) => {
    this.setState(
      {
        filter: Object.assign({}, this.state.filter, newFilters),
      },
      this._fetchFilesAndAggregatesAsync
    );
  };

  render() {
    return (
      <div>
        {store.hasPermission("upload.view_all_uploads") ? (
          <div className="tabs is-centered">
            <ul>
              <li className={!this.state.filter.download ? "is-active" : ""}>
                <Link to="/uploads/files" onClick={this.filterOnAll}>
                  All Files
                </Link>
              </li>
              <li>
                <Link to="/uploads">All Uploads</Link>
              </li>
            </ul>
          </div>
        ) : null}
        <h1 className="title">{this.pageTitle}</h1>

        {this.state.loadingFiles ? (
          <Loading />
        ) : (
          this.state.files && (
            <TableSubTitle
              total={this.state.total}
              page={this.state.filter.page}
              batchSize={this.state.batchSize}
              calculating={this.state.loadingAggregates}
            />
          )
        )}

        {!this.state.loadingFiles && this.state.files && (
          <DisplayFiles
            loading={this.state.loadingFiles}
            files={this.state.files}
            batchSize={this.state.batchSize}
            location={this.props.location}
            filter={this.state.filter}
            updateFilter={this.updateFilter}
            hasNextPage={this.state.hasNextPage}
          />
        )}

        {this.state.loadingAggregates && !this.state.loadingFiles && (
          <Loading />
        )}

        {!this.state.loadingAggregates && this.state.files && (
          <DisplayFilesAggregates
            aggregates={this.state.aggregates}
            total={this.state.total}
          />
        )}
      </div>
    );
  }
}

export default Files;

class DisplayFiles extends React.PureComponent {
  componentDidMount() {
    // XXX perhaps this stuff should happen in a componentWillReceiveProps too
    const filter = this.props.filter;
    this.refs.key.value = filter.key || "";
    this.refs.size.value = filter.size || "";
    this.refs.created_at.value = filter.created_at || "";
    this.refs.bucketName.value = filter.bucket_name || "";
  }

  submitForm = (event) => {
    event.preventDefault();
    const key = this.refs.key.value.trim();
    const size = this.refs.size.value.trim();
    const created_at = this.refs.created_at.value.trim();
    const bucketName = this.refs.bucketName.value.trim();
    this.props.updateFilter({
      page: 1,
      key,
      size,
      created_at,
      bucket_name: bucketName,
    });
  };

  resetFilter = (event) => {
    this.refs.key.value = "";
    this.refs.size.value = "";
    this.refs.bucketName.value = "";
    this.refs.created_at.value = "";
    this.submitForm(event);
  };
  render() {
    const { loading, files } = this.props;

    return (
      <form onSubmit={this.submitForm}>
        <table className="table is-fullwidth is-narrow files-table">
          <thead>
            <tr>
              <th>Key</th>
              <th>Size</th>
              <th>Bucket</th>
              <th>Uploaded</th>
              <th
                className="bool-row is-clipped"
                title="True if the file overwrote an existing one with the same name"
              >
                Update
              </th>
              <th
                className="bool-row is-clipped"
                title="True if the file was first gzipped before uploading"
              >
                Compressed
              </th>
              <th>Time to complete</th>
            </tr>
          </thead>
          <tfoot>
            <tr>
              <td>
                <input
                  type="text"
                  className="input"
                  ref="key"
                  placeholder="filter..."
                />
              </td>
              <td>
                <input
                  type="text"
                  className="input"
                  ref="size"
                  placeholder="filter..."
                  style={{ width: 140 }}
                />
              </td>
              <td>
                <input
                  type="text"
                  className="input"
                  ref="bucketName"
                  placeholder="filter..."
                  style={{ width: 140 }}
                />
              </td>
              <td>
                <input
                  type="text"
                  className="input"
                  ref="created_at"
                  placeholder="filter..."
                  style={{ width: 140 }}
                />
              </td>
              <td colSpan={3} style={{ minWidth: 230 }}>
                <button type="submit" className="button is-primary">
                  Filter
                </button>{" "}
                <button
                  type="button"
                  onClick={this.resetFilter}
                  className="button"
                >
                  Reset
                </button>
              </td>
            </tr>
          </tfoot>
          <tbody>
            {!loading &&
              files.map((file) => (
                <tr key={file.id}>
                  <td className="file-key">
                    <Link to={`/uploads/files/file/${file.id}`}>
                      {file.key}
                    </Link>
                  </td>
                  <td>{formatFileSize(file.size)}</td>
                  <td>{file.bucket_name}</td>
                  <td>
                    {file.upload ? (
                      <Link
                        to={`/uploads/upload/${file.upload.id}`}
                        title={`Uploaded by ${file.upload.user.email}`}
                      >
                        <DisplayDate date={file.created_at} />
                      </Link>
                    ) : (
                      <DisplayDate date={file.created_at} />
                    )}{" "}
                    {file.upload && file.upload.try_symbols ? (
                      <span
                        className="tag is-info"
                        title="Part of a Try build upload"
                      >
                        Try
                      </span>
                    ) : null}
                  </td>
                  <td>{BooleanIcon(file.update)}</td>
                  <td>{BooleanIcon(file.compressed)}</td>
                  <td>
                    {file.completed_at ? (
                      <DisplayDateDifference
                        from={file.created_at}
                        to={file.completed_at}
                      />
                    ) : (
                      <i>Incomplete!</i>
                    )}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>

        {!loading && (
          <Pagination
            location={this.props.location}
            total={this.props.total}
            batchSize={this.props.batchSize}
            updateFilter={this.props.updateFilter}
            currentPage={this.props.filter.page}
            hasNext={this.props.hasNextPage}
          />
        )}
      </form>
    );
  }
}

class DisplayFilesAggregates extends React.PureComponent {
  render() {
    const { aggregates } = this.props;
    return (
      <nav className="level" style={{ marginTop: 60 }}>
        <div className="level-item has-text-centered">
          <div>
            <p className="heading">Files</p>
            <p className="title">
              {aggregates.files.count
                ? thousandFormat(aggregates.files.count)
                : "n/a"}
            </p>
          </div>
        </div>
        <div className="level-item has-text-centered">
          <div title="Files that got started upload but never finished for some reason">
            <p className="heading">Incomplete Files</p>
            <p className="title">
              {thousandFormat(aggregates.files.incomplete)}
            </p>
          </div>
        </div>
        <div className="level-item has-text-centered">
          <div>
            <p className="heading">File Sizes Sum</p>
            <p className="title">
              {aggregates.files.size.sum
                ? formatFileSize(aggregates.files.size.sum)
                : "n/a"}
            </p>
          </div>
        </div>
        <div className="level-item has-text-centered">
          <div>
            <p className="heading">File Sizes Avg</p>
            <p className="title">
              {aggregates.files.size.average
                ? formatFileSize(aggregates.files.size.average)
                : "n/a"}
            </p>
          </div>
        </div>
        <div
          className="level-item has-text-centered"
          title="Average time to complete upload of completed files"
        >
          <div>
            <p className="heading">Upload Time Avg</p>
            <p className="title">
              {aggregates.files.time.average
                ? formatSeconds(aggregates.files.time.average)
                : "n/a"}
            </p>
          </div>
        </div>
      </nav>
    );
  }
}
