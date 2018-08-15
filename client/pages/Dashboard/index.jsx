// React lib import
import React, { Component } from 'react';
import { connect } from 'react-redux';
import PropTypes from 'prop-types';

// third-party imports
import { Route, Redirect, Switch } from 'react-router-dom';

// components
import Header from '../../components/common/Header';
import { HomePage } from '../../components/common/HomePage';
import ModalContextProvider from '../../components/Modals/ModalContext';
import Modal from '../../components/Modals/ModalContainer';

// stylesheet
import '../../assets/style.scss';

// thunk
import {
  loadActiveUser,
  displayLoginErrorMessage,
} from '../../actions/userActions';

// utils
import isLoggedIn from '../../utils/isLoggedIn';
import isTokenExpired from '../../utils/isTokenExpired';

/**
 * Represents Dashboard component
 *
 * @class Dashboard
 * @extends {React.Component}
 */
class Dashboard extends Component {
  constructor(props) {
    super(props);
    this.state = { activeUser: {} };
  }

  /**
   * React Lifecycle hook
   *
   * @memberof Dashboard
   * @returns {null}
   */
  componentDidMount() {
    this.props.loadActiveUser();
  }


  /**
   * React Lifecycle hook
   *
   * @param {nextProps, prevState}
   * @memberof Dashboard
   * @returns {null}
   */
  static getDerivedStateFromProps(nextProps, prevState) {
    if (Object.keys(nextProps.activeUser).length > 0
      && (nextProps.activeUser !== prevState.activeUser)) {
      return { activeUser: nextProps.activeUser };
    }
  }

  /**
   * Method to render user dashboard
   *
   * @memberof Dashboard
   * @returns {jsx} jsx
   */
  redirectUser = () => {
    const { location: { pathname } } = this.props;
    if (pathname === '/') {
      return (<Redirect to="/home" />);
    }
  };


  /**
   * Renders Dashboard component
   *
   * @returns {JSX} jsx
   * @memberof Dashboard
   */
  render() {
    const { location: { search } } = this.props;

    if (search.split('?token=')[1]) {
      localStorage.setItem('token', search.split('?token=')[1]);
    }

    if (isTokenExpired() || !isLoggedIn()) {
      return (
        <Redirect to="/login" />
      );
    }

    if (search === '?error=failed+to+create+user+token') {
      this.props.displayLoginErrorMessage();
    }

    return (
      <ModalContextProvider>
        <Header />
        <Switch>
          {this.redirectUser()}
          <Route path="/home" render={() => <HomePage />} />
        </Switch>
        <Modal />
      </ModalContextProvider>
    );
  }
}

Dashboard.propTypes = {
  location: PropTypes.shape({ pathname: PropTypes.string.isRequired }).isRequired,
  loadActiveUser: PropTypes.func.isRequired,
};

const mapStateToProps = state => ({ activeUser: state.activeUser });

export default connect(mapStateToProps,
  {
    loadActiveUser, displayLoginErrorMessage,
  })(Dashboard);