import numpy as np
from scipy.interpolate import pchip_interpolate
from . import INST_FREQ_local

def tvfemd(x, THRESH_BWR=0.1, BSP_ORDER=26, MODES=50): ## t useless
	"""Time varying filter based EMD
	Parameters
	----------
	x : numpy ndarray
		Input signal x(t)
	THRESH_BWR : float, optional
		Instantaneous bandwidth threshold (default : 0.1)
	BSP_ORDER : int, optional
		b-spline order (default : 26)
	MODES : int, optional
		(default : 50)
	Returns
	-------
	imf : numpy ndarray
		imfs matrix
	"""
	numMAX = int(np.floor(np.log2(len(x))) + 1)
	MAX_IMF = numMAX + MODES

	end_flag = 0
	imf = np.zeros((MAX_IMF, len(x)), dtype=float)
	temp_x = x.copy()

	t = np.arange(1, len(x) + 1, dtype=int)
	for nimf in range(MAX_IMF):
		indmin_x, indmax_x = extr(temp_x)
		if nimf == (MAX_IMF - 1):
			imf[nimf, :] = temp_x
			nimf += 1
			break

		if len(np.concatenate([indmin_x, indmax_x])) < 4:
			imf[nimf, :] = temp_x
			if len(np.where(temp_x != 0)[0]) > 0:
				nimf += 1
			end_flag = 1

		if end_flag == 1:
			break

		num_padding = int(np.round(len(temp_x) * 0.5))
		y = temp_x.copy()

		flag_stopiter = 0
		for iter in range(100):
			y = np.concatenate([np.flip(y[1:2+num_padding]), y, np.flip(y[-num_padding-1:-1])])

			tt = np.arange(1, len(y), dtype=int)
			ind_remov_pad = np.arange(num_padding + 1, len(y) - num_padding, dtype=int)

			indmin_y, indmax_y = extr(y)
			indexC_y = np.sort(np.concatenate([indmin_y, indmax_y]))
			inst_amp_0, inst_freq_0 = INST_FREQ_local(y)

			a1, f1, a2, f2, bis_freq, instBWR, avgFreq = divide_y(y, instAmp0, instFreq0)

			instBWR2 = instBWR.copy()
			for j in np.arange(0, len(indexC_y) - 2, 2):
				ind = np.arange(indexC_y[j], indexC_y[j + 2], dtype=int)
				instBWR2[ind] = np.mean(instBWR[ind])

			bis_freq[instBWR2 < THRESH_BWR] = 1e-12
			bis_freq[bis_freq > 0.5] = 0.45
			bis_freq[bis_freq <= 0] = 1e-12

			bis_freq = anti_modemixing(y, bis_freq, ind_remov_pad, num_padding)
			bis_freq = bis_freq[ind_remov_pad]
			bis_freq = np.concatenate([np.fliplr(bis_freq[1:2+num_padding-1]), bis_freq, np.fliplr(bis_freq[-num_padding-1:-1])])

			bis_freq = anti_modemixing(y, bis_freq, ind_remov_pad, num_padding)
			bis_freq = bis_freq[ind_remov_pad]
			bis_freq = np.concatenate([np.fliplr(bis_freq[1:2+num_padding-1]), bis_freq, np.fliplr(bis_freq[-num_padding-1:-1])])

			temp_instBWR = instBWR2[ind_remov_pad]
			ind_start = np.round(len(temp_instBWR) * 0.05)
			ind_end = np.round(len(temp_instBWR) * 0.95)

			if ((iter >= 2 and np.mean(temp_instBWR[ind_start:ind_end+1]) < THRESH_BWR + THRESH_BWR / 4 * iter) or
				iter >= 6 or
				(nimf > 1 and np.mean(temp_instBWR[ind_start:ind_end+1]) < THRESH_BWR + THRESH_BWR / 4 * iter)):
				flag_stopiter = 1

			if len(np.where(temp_instBWR[ind_start:ind_end+1] > THRESH_BWR)[0]) / len(instBWR2[ind_remov_pad]) < 0.2:
				flag_stopiter = 1;

			phi = np.zeros((len(bis_freq), ))
			for i in range(len(bis_freq) - 1):
				phi[i + 1] = phi[i] + 2 * pi * bis_freq[i]

			indmin_knot, indmax_knot = extr(cos(phi))
			indexC_knot = np.sort(np.concatenate([indmin_knot, indmax_knot]))
			if len(indexC_knot) > 2:
				pp_spline = splinefit(np.arange(0, length(y), dtype=int), y, indexC_knot, BSP_ORDER, 'p')
				localmean = ppval(pp_spline, np.arange(0, length(y), dtype=int))
			else:
				flag_stopiter = 1

			if (np.max(np.abs(y[ind_remov_pad] - localmean[ind_remov_pad])) / np.min(np.abs(localmean[ind_remov_pad])) < 1e-3):
				flag_stopiter = 1

			temp_residual = y - localmean
			temp_residual = temp_residual[ind_remov_pad]
			temp_residual = temp_residual[np.round(len(temp_residual) * 0.1):-np.round(len(temp_residual) * 0.1)]
			localmean2 = localmean[ind_remov_pad]
			localmean2 = localmean2[np.round(len(localmean2) * 0.1):-np.round(len(localmean2) * 0.1)]
			if (np.abs(np.max(localmean2)) / np.abs(np.max(inst_amp_0[ind_remov_pad])) < 3.5e-2 or
			   np.abs(np.max(temp_residual)) / np.abs(np.max(inst_amp_0[ind_remov_pad])) < 1e-2):
				flag_stopiter = 1

			if flag_stopiter:
				imf[nimf,:] = y[ind_remov_pad]
				temp_x -= y[ind_remov_pad]
				break

			y -= localmean
			y = y[ind_remov_pad]

	imf = np.delete(imf, np.s_[nimf:MAX_IMF], axis=0)

	return imf

def anti_modemixing(y, bis_freq, ind_remov_pad, num_padding):
	"""

	"""
	org_bis_freq = bis_freq.copy()
	output_cutoff = bis_freq.copy()
	flag_intermitt = 0
	t = np.arange(1, len(bis_freq), dtype=int)
	intermitt = np.array([], dtype=int)

	indmin_y, indmax_y = extr(y)
	indexC_y = np.sort(np.concatenate([indmin_y, indmax_y]))
	zero_span = np.array([], dtype=int)

	for i in range(1, len(indmax_y) - 1):
		time_span = np.arange(indmax_y[i - 1], indmax_y[i + 1], dtype=int)
		if (np.max(bis_freq[time_span]) - np.min(bis_freq[time_span])) / np.min(bis_freq[time_span]) > 0.25:
			zero_span = np.concatenate([zero_span, time_span])
	bis_freq[zero_span] = 0

	diff_bis_freq = np.zeros(bis_freq.shape)
	for i in range(len(indmax_y) - 1):
		time_span = np.arange(indmax_y[i], indmax_y[i + 1], dtype=int)
		if (np.max(bis_freq[time_span]) - np.min(bis_freq[time_span])) / np.min(bis_freq[time_span]) > 0.25:
			intermitt = np.concatenate([intermitt, indmax_y[i]])
			diff_bis_freq[indmax_y[i]] = bis_freq[indmax_y[i + 1]] - bis_freq[indmax_y[i]]

	ind_remov_pad = np.delete(ind_remov_pad, np.r_[np.s_[0:np.round(0.1 * len(ind_remov_pad))], np.s_[np.round(0.9 * len(ind_remov_pad))-1:len(ind_remov_pad)]])
	inters = np.intersect1d(ind_remov_pad, intermitt)
	if len(inters) > 0:
		flag_intermitt = 1

	for i in range(1, len(intermitt) - 1):
		u1 = intermitt[i - 1]
		u2 = intermitt[i]
		u3 = intermitt[i + 1]
		if diff_bis_freq[u2] > 0:
			bis_freq[u1:u2+1] = 0
		if diff_bis_freq[u2] < 0:
			bis_freq[u2:u3+1] = 0

	temp_bis_freq = bis_freq.copy()
	temp_bis_freq[temp_bis_freq < 1e-9] = 0
	temp_bis_freq = temp_bis_freq[ind_remov_pad]
	temp_bis_freq = np.concatenate([np.fliplr(temp_bis_freq[1:2+num_padding]), temp_bis_freq, np.fliplr(temp_bis_freq[-num_padding-1:-1])])
	flip_bis_freq = np.fliplr(bis_freq)
	id_t = np.where(temp_bis_freq > 1e-9)[0]
	id_f = np.where(flip_bis_freq > 1e-9)[0]
	if len(id_t) > 0 and len(id_f) > 0:
		temp_bis_freq[0] = bis_freq[np.where(bis_freq > 1e-9)[0][0]]
		temp_bis_freq[-1] = flip_bis_freq[np.where(flip_bis_freq > 1e-9)[0][0]]
	else:
		temp_bis_freq[0] = bis_freq[0]
		temp_bis_freq[-1] = bis_freq[-1]

	bis_freq = temp_bis_freq.copy()
	if len(t[bis_freq != 0]) < 2:
		return

	bis_freq = pchip_interpolate(t[bis_freq!=0], bis_freq[bis_freq!=0], t)

	flip_bis_freq = np.fliplr(org_bis_freq)
	if len(np.where(org_bis_freq > 1e-9)[0]) > 0 and len(np.where(flip_bis_freq > 1e-9)[0]) > 0:
		org_bis_freq[0] = org_bis_freq[np.where(org_bis_freq > 1e-9)[0][0]]
		org_bis_freq[-1] = flip_bis_freq[np.where(flip_bis_freq > 1e-9)[0][0]]

	org_bis_freq[org_bis_freq < 1e-9] = 0
	org_bis_freq[0] = bis_freq[0]
	org_bis_freq[-1] = bis_freq[-1]
	org_bis_freq = pchip_interpolate(t[org_bis_freq!=0], org_bis_freq[org_bis_freq!=0], t)

	if flag_intermitt and np.max(temp_bis_freq[ind_remov_pad]) > 1e-9:
		output_cutoff = bis_freq.copy()
	else:
		output_cutoff = org_bis_freq.copy()

	output_cutoff[output_cutoff > 0.45] = 0.45
	output_cutoff[output_cutoff < 0] = 0

	return output_cutoff

def divide_y(y, inst_amp_0, inst_freq_0):
	"""divide y(t) into two sub-signals a1(t)exp(2*pi*f1(t)) and a2(t)exp(2*pi*f2(t)).
	Parameters
	----------
	y : numpy ndarray
		Input signal.
	inst_amp_0 : float
		Instantaneous amplitude of `y`.
	inst_freq_0 : float
		Instantaneous frequency of `y`.
	Returns
	-------
	a1 : float
		Instantaneous amplitude of the first sub-signal.
	f1 : float
		Instantaneous frequency of the first sub-signal.
	a2 : float
		Instantaneous amplitude of the first sub-signal.
	f2 : float
		Instantaneous frequency of the second sub-signal.
	bis_freq : float
		Bisecting frequency, (`f1` + `f2`) / 2.
	ratio_bw : float
		Instantaneous bandwidth ratio (stopping criterion).
	"""
	bis_freq = np.zeros((len(inst_amp_0, )), dtype=float)
	tt = np.arange(1, len(inst_amp_0), dtype=int)
	squar_inst_amp_0 = np.power(inst_amp_0, 2.0)

	indmin_y, indmax_y = extr(y)
	indmin_amp_0, indmax_amp_0 = extr(squar_inst_amp_0)

	if len(indmin_amp_0) < 2 or len(indmax_amp_0) < 2:
		a1 = np.zeros((len(inst_amp_0), ), dtype=float)
		a2 = np.zeros((len(inst_amp_0), ), dtype=float)
		f1 = inst_freq_0.copy()
		f2 = inst_freq_0.copy()
		ratio_bw = a1.copy()
		bis_freq = np.zeros((len(inst_amp_0), ), dtype=float)
		avg_freq = np.zeros((len(inst_amp_0), ), dtype=float)

		return a1, f1, a2, f2, bis_freq, ratio_bw, avg_freq

	envpmax_inst_amp = pchip_interpolate(indmax_amp_0, inst_amp_0[indmax_amp_0], tt)
	envpmin_inst_amp = pchip_interpolate(indmin_amp_0, inst_amp_0[indmin_amp_0], tt)

	a1 = (envpmax_inst_amp + envpmin_inst_amp) / 2.0
	a2 = (envpmax_inst_amp - envpmin_inst_amp) / 2.0
	indmin_a2, indmax_a2 = extr(a2)

	inst_amp_inst_amp_2 = inst_freq_0 * np.power(inst_amp_0, 2.0)
	inst_amp_tmax = pchip(indmax_amp_0, inst_amp_inst_amp_2[indmax_amp_0], np.arange(1, len(inst_amp_inst_amp_2), dtype=int))
	inst_amp_tmin = pchip(indmin_amp_0, inst_amp_inst_amp_2[indmin_amp_0], np.arange(1, len(inst_amp_inst_amp_2), dtype=int))
	f1 = np.zeros((len(inst_freq_0), ), dtype=float)
	f2 = np.zeros((len(inst_freq_0), ), dtype=float)
	for i in range(len(inst_freq_0)):
		A = np.empty((2, 2 * len(a1)), dtype=float)
		A[0, :] = np.concatenate([np.power(a1[i], 2.0) + a1[i] * a2[i], np.power(a2[i], 2.0) + a1[i] * a2[i]])
		A[1, :] = np.concatenate([np.power(a1[i], 2.0) - a1[i] * a2[i], np.power(a2[i], 2.0) - a1[i] * a2[i]])
		B = np.concatenate([inst_amp_tmax[i], inst_amp_tmin[i]])
		C = np.linalg.solve(A, B)
		f1[i] = C[0]
		f2[i] = C[1]

	bis_freq = (inst_amp_tmax - inst_amp_tmin) / (4 * a1 * a2)
	if len(indmax_a2) > 3:
		bis_freq = pchip_interpolate(indmax_a2, bis_freq[indmax_a2], tt)

	avg_freq = (inst_amp_tmax + inst_amp_tmin) / (2 * (np.power(a1, 2.0) + np.power(a2, 2.0)))
	cos_diffphi = (np.power(inst_amp_0, 2.0) - np.power(a1, 2.0) - np.power(a2, 2.0)) / (2 * a1 * a2)
	cos_diffphi[cos_diffphi > 1.2] = 1
	cos_diffphi[cos_diffphi < -1.2] = -1
	inst_amp1, inst_freq_diff_phi = INST_FREQ_local(cos_diffphi)

	diff_a1 = (a1[2:] - a1[:-2]) / 2.0
	diff_a1 = np.concatenate([diff_a1[0], diff_a1, diff_a1[-1]])
	diff_a2 = (a2[2:] - a2[:-2]) / 2.0
	diff_a2 = np.concatenate([diff_a2[0], diff_a2, diff_a2[-1]])

	inst_BW = ((np.power(diff_a1, 2.0) + np.power(diff_a2, 2.0)) / (np.power(a1, 2.0) + np.power(a2, 2.0)) + np.power(a1, 2.0) * np.power(a2, 2.0) * np.power(inst_freq_diff_phi, 2.0) / np.power(np.power(np.power(a1, 2.0) + np.power(a2, 2.0)), 2.0), 0.5)
	ratio_bw = np.abs(inst_BW / avg_freq)
	ratio_bw[(a2 / a1) < 5e-3] = 0
	ratio_bw[avg_freq < 1e-7] = 0
	ratio_bw[ratio_bw > 1] = 1

	ff1 = (inst_freq_diff_phi + 2.0 * bis_freq) / 2.0
	ff2 = (2.0 * bis_freq - inst_freq_diff_phi) / 2.0
	f1[np.abs((a1 - a2) / a1) < 0.05] = ff1[np.abs((a1 - a2) / a1) < 0.05]
	f2[np.abs((a1 - a2) / a1) < 0.05] = ff2[np.abs((a1 - a2) / a1) < 0.05]

	temp_inst_amp_0 = inst_amp_0
	for j in range(len(indmax_y) - 1):
		ind = np.arange(indmax_y[j], indmax_y[j + 1] + 1, dtype=int)
		temp_inst_amp_0[ind] = np.mean(inst_amp_0[ind])

	ratio_bw[np.abs(temp_inst_amp_0) / np.max(np.abs(y)) < 5e-2] = 0
	f1[np.abs(temp_inst_amp_0) / np.max(np.abs(y)) < 4e-2] = 1 / len(y) / 1000
	f2[np.abs(temp_inst_amp_0) / np.max(np.abs(y)) < 4e-2] = 1 / len(y) / 1000
	bis_freq[bis_freq > 0.5] = 0.5
	bis_freq[bis_freq < 0] = 0

	return a1, f1, a2, f2, bis_freq, ratio_bw, avg_freq

def extendsignal(y, n_padding): ####### indices #######
	"""Pads a signal to decrease border effects.
	Parameters
	----------
	y : numpy ndarray
		A real vector that will be extended.
	n_padding : int
		Number of points that are going to be added to one side of the signal.
	Returns
	-------
	padded : numpy ndarray
		A version of `y` that has been extended.
	"""
	left_padded = 0
	right_padded = 0
	n_added_end = 0
	n_added_start = 0
	padded = y.copy()

	while left_padded == 0 or right_padded == 0:
		n_points = len(y)
		end_slope = y[-1] - y[-2]
		end_inds = fast_crossing(y, y[-1])
		n_add_end = n_points - 1
		end_inds = np.delete(end_inds, np.where(end_inds == n_points - 1)[0])
		n_add_end = match_slope(y, end_inds, end_slope) + 1
		if np.isempty(n_add_end):
			if right_padded == 0:
				if(n_points - 1 + n_added_end >= n_padding):
					right_padded = 1
				n_add_end_2 = np.max(0, n_points - 1 - n_padding + 1)
				padded = np.concatenate([padded, y[n_add_end_2:-1:-1]])
				n_added_end += len(y[n_add_end_2:-1:-1])

		start_slope = y[1] - y[0]
		start_inds = fast_crossing(y, y[0])
		n_add_start = 2
		start_inds = np.delete(start_inds, np.where(start_inds + 1 == 2)[0])
		n_add_start = match_slope(y, start_inds + 1, start_slope) - 2
		if np.isempty(n_add_start):
			if(left_padded == 0):
				if(n_points - 1 + n_added_start >= n_padding):
					left_padded = 1
				n_add_start_2 = np.min(n_points, n_padding + 1)
				padded = np.concatenate([y[1:n_add_start_2:-1], padded])
				n_added_start += len(y[1:n_add_start_2:-1])

		if left_padded:
			n_add_start_2 = n_add_start
		else:
			n_add_start_2 = 1

		if n_add_start + n_added_start >= n_padding:
			n_add_start_2 = n_add_start + n_added_start - n_padding + 1
			left_padded = 1

		if right_padded:
			n_add_end_2 = n_add_end
		else:
			n_add_end_2 = n_points

		if n_points - n_add_end + 1 + n_added_end >= n_padding:
			n_add_end_2 = n_add_end + n_padding - 1 - n_added_end
			right_padded = 1

		padded = np.concatenate([y[n_add_start_2:n_add_start], padded, y[n_add_end:n_add_end_2]])
		n_added_end += n_add_end_2 - n_add_end + 1
		n_added_start += n_add_start - n_add_start_2 + 1

	return padded

def fast_crossing(s, level):
	"""Calculate when S crosses level.
	"""
	s -= level

	return zerocross(s)

def match_slope(y, inds, slope):
	"""

	"""
	n_points = len(y)
	inds = np.delete(inds, np.where((y[inds] - y[inds - 1]) * slope < 0)[0])
	inds = np.delete(inds, np.where(inds > n_points - 5)[0])
	inds = np.delete(inds, np.where(inds < 5)[0])
	slopes = y[inds] - y[inds - 1]
	slope_diff = np.min(np.abs(slopes - slope))
	ind = np.where(np.abs(slopes - slope) == slope_diff)[0]
	if np.isfinite(slope_diff):
		out_ind = inds[ind]
	else:
		out_ind = np.array([], dtype=int)

	return out_ind


def extr(x, t=[]): ### t useless, also indzer
	"""Extracts the indices of extrema.
	Parameters
	----------
	x : numpy ndarray
		Input signal.
	t : numpy ndarray, optional
		(default : range(len(x))).
	Returns
	-------
	indmin : numpy ndarray
		Indices of minima.
	indmax : numpy ndarray
		Indices of maxima.
	indzer : numpy ndarray
		Indices of zeros.
	"""

	m = len(x)
	if len(t) == 0:
		t = np.arange(1, m + 1, dtype=int)

	x1 = x[:m-1]
	x2 = x[1:]
	indzer = np.where(x1 * x2 < 0.0)[0]

	if np.any(x == 0.0):
		iz = np.where(x == 0.0)[0]
		
		if np.any(np.diff(iz) == 1):
			zer = x == 0.0
			dz = np.diff(np.concatenate([[0], zer, [0]]))
			debz = np.where(dz == 1)[0]
			finz = np.where(dz == -1)[0] - 1
			indz = np.round((debz + finz) / 2)
		else:
			indz = iz

		indzer = np.sort(np.concatenate([indzer, indz]))

	d = np.diff(x)
	n = len(d)
	d1 = d[:n-1]
	d2 = d[1:]
	indmin = np.where((d1 * d2 < 0.0) & (d1 < 0.0))[0] + 1
	indmax = np.where((d1 * d2 < 0.0) & (d1 > 0.0))[0] + 1

	if any(d == 0.0):
		imax = np.array([], dtype=int)
		imin = np.array([], dtype=int)

		bad = d == 0.0
		dd = np.diff(np.concatenate([[0], bad, [0]]))
		debs = np.where(dd == 1)[0]
		fins = np.where(dd == -1)[0]

		if debs[0] == 1:
			if len(debs) > 1:
				debs = debs[1:]
				fins = fins[1:]
			else:
				debs = np.array([], dtype=int)
				fins = np.array([], dtype=int)

		if len(debs) > 0:
			if fins[-1] == m:
				if len(debs) > 1:
					debs = debs[:-1]
					fins = fins[:-1]
				else:
					debs = np.array([], dtype=int)
					fins = np.array([], dtype=int)

		lc = len(debs)
		if lc > 0:
			for k in range(lc):
				if d[debs[k]-1] > 0:
					if d[fins[k]] < 0:
						imax = np.concatenate([imax, np.round((fins[k] + debs[k]) / 2)])
				else:
					if d[fins[k]] > 0:
						imin = np.concatenate([imin, np.round((fins[k] + debs[k]) / 2)])

		if len(imax) > 0:
			indmax = np.sort(np.concatenate([indmax, imax]))
		if len(imin) > 0:
			indmin = np.sort(np.concatenate([indmin, imin]))

	return indmin, indmax#, indzer
