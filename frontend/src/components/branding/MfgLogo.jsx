import logo from '../../assets/mfg-logo.svg'


export default function MfgLogo({
  className = '',
  alt = 'MFG Technik & Service',
}) {
  return (
    <img
      src={logo}
      alt={alt}
      className={className}
    />
  )
}
