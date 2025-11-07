WITH deliris as(
	SELECT 
		patient_ref
		,episode_ref
		,result_date
		,ou_loc_ref
		,result_txt
	FROM
		g_rc
	WHERE
		rc_sap_ref = 'DELIRIO_CAM-ICU'
		AND result_txt IN ('DELIRIO_CAM-ICU_1', 'DELIRIO_CAM-ICU_2', 'DELIRIO_CAM-ICU_3')

)

SELECT *
FROM deliris
WHERE 
	ou_loc_ref IN (
	'E073', 'I073'						-- Hepàtica
	,'E014', 'E015', 'I014', 'I015'		-- AVI
	,'E103', 'I103'						-- Cardiaca
	,'E043', 'I043'						-- UCIQ	
	,'E057', 'I057', 'E037', 'I037'		-- UVIR 
	,'E016', 'I016')					-- Coronaria
	AND result_date BETWEEN  '2024-01-01 00:00:00' AND '2024-12-31 23:59:59'
