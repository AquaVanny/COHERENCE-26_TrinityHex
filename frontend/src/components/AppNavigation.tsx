import { Link, useLocation } from 'react-router-dom'
import { Activity, Users, Search, Home, Settings } from 'lucide-react'

const AppNavigation = () => {
  const location = useLocation()

  const navItems = [
    { path: '/', label: 'Dashboard', icon: Home },
    { path: '/matcher', label: 'Patient Matcher', icon: Users },
    { path: '/trials', label: 'Trial Explorer', icon: Search },
    { path: '/manage-trials', label: 'Manage Trials', icon: Settings }
  ]

  return (
    <nav className="navbar">
      <Link to="/" className="logo">
        <div className="logo-icon">
          <Activity className="h-[18px] w-[18px]" />
        </div>
        <span className="logo-text">
          <span>Clinical Trial</span> Matcher
        </span>
      </Link>

      <ul className="nav-links">
        {navItems.map(({ path, label, icon: Icon }) => (
          <li key={path}>
            <Link
              to={path}
              className={`nav-link ${location.pathname === path ? 'active' : ''}`}
            >
              <Icon className="h-[15px] w-[15px]" />
              <span>{label}</span>
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  )
}

export default AppNavigation
